"""Login.gov OTP login used by the hub fixture (not by tests).

Port of Katalon Login.loginToCrdcOtp: same screens and retry idea, Playwright waits
instead of WebUI.delay. After a successful Grant, Hub sets the connect.sid cookie.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.config import Settings
from crdc_pw.hub import Hub
from crdc_pw.locators.loader import LocatorLoader
from crdc_pw.otp import totp_now
from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.login import (
    GRANT,
    NIH_AGREE,
    OTP,
    POST_OTP_STEPS,
    POST_PASSWORD_STEPS,
    RULES_ACCEPT,
    SYSTEM_USE_CONTINUE,
    USERNAME,
    LoginPage,
)

log = logging.getLogger("crdc_pw.auth")

OTP_MAX_ATTEMPTS = 6  # Katalon used 6; TOTP changes every 30s
OTP_RETRY_WAIT_MS = 30_000
LOGIN_GOV_STEP_TIMEOUT_MS = 60_000  # Grant can lag 30s+ on a slow Hub


class LoginSession:
    """OTP / Grant flow for the fixture. Tests do not construct this."""

    def __init__(self, page: Page, locators: LocatorLoader, settings: Settings) -> None:
        self.page = page
        self.locators = locators
        self.settings = settings
        self.login_page = LoginPage(page, locators)
        self.header = HeaderPage(page, locators)

    def navigate(self) -> None:
        self.login_page.goto(self.settings.base_url)
        self.login_page.dismiss_system_use_warning()

    def is_logged_in(self, timeout_ms: int = 2000) -> bool:
        return self.header.is_logged_in(timeout_ms=timeout_ms)

    def signed_in_as(self, role: str) -> bool:
        """True if Hub header is visible and the name is this PBAC automation user."""
        if not self.is_logged_in(timeout_ms=2000):
            return False
        username = self.header.username(timeout_ms=5000)
        return username_matches_role(username, role)

    def _drop_browser_session(self) -> None:
        """Drop Hub + NIH/Login.gov cookies so SSO cannot restore the previous role.

        Katalon switchUser does closeBrowser(); this is the same-tab equivalent.
        """
        log.info("Clearing cookies so NIH SSO cannot restore the last role")
        try:
            self.page.evaluate(
                "() => { try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} }"
            )
        except Exception:
            pass
        self.page.context.clear_cookies()

    def login_otp(self, role: str) -> None:
        """Full Login.gov path for one role (Admin, Fedlead, ...). Fixture and switch_user only."""
        creds = self.settings.role(role)
        if not creds.is_complete():
            raise ValueError(
                f"Missing {role}Email / {role}Password / {role}Secret in {self.settings.config_path.name}"
            )
        log.info("Login %s: opening Hub and Login.gov", role)
        self.navigate()
        if self.signed_in_as(role):
            log.info("Login %s: already signed in as this role", role)
            return
        if self.is_logged_in(timeout_ms=2000):
            username = self.header.username(timeout_ms=5000)
            log.info("Login %s: Hub is %r, not this role; dropping session", role, username)
            self.logout()
            self._drop_browser_session()
            self.navigate()
        self.login_page.start_login_gov()
        if self.signed_in_as(role):
            username = self.header.username(timeout_ms=5000)
            log.info(
                "Login %s: Hub after Login click (SSO session reuse), username=%r",
                role,
                username,
            )
            return
        if self.is_logged_in(timeout_ms=2000):
            username = self.header.username(timeout_ms=5000)
            log.info(
                "Login %s: SSO restored %r instead of this role; dropping session and using Login.gov",
                role,
                username,
            )
            self.logout()
            self._drop_browser_session()
            self.navigate()
            self.login_page.start_login_gov()
        self.login_page.submit_credentials(creds.email, creds.password)
        log.info("Login %s: submitted credentials, waiting for OTP or Grant (up to 60s)", role)

        logged_in = False
        for attempt in range(OTP_MAX_ATTEMPTS):
            self.login_page.maybe_accept_rules_of_use()
            # Do not assume OTP is next — Login.gov may skip it and show Grant.
            step = self.login_page.wait_for_any(POST_PASSWORD_STEPS, LOGIN_GOV_STEP_TIMEOUT_MS)
            log.info("Login %s: after password, saw %s (attempt %s)", role, _step_name(step), attempt + 1)

            if step == RULES_ACCEPT:
                self.login_page.maybe_accept_rules_of_use()
                continue
            if step == NIH_AGREE:
                self.login_page.maybe_agree_nih_info_request()
                continue
            if self._finish_if_hub_or_grant(step):
                logged_in = True
                break

            code = totp_now(creds.secret)
            self.login_page.submit_otp(code)
            log.info("Login %s: submitted OTP, waiting for Grant or Hub (up to 60s)", role)
            self.login_page.maybe_agree_nih_info_request()
            try:
                post_otp = self.login_page.wait_for_any(POST_OTP_STEPS, LOGIN_GOV_STEP_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                log.error("Login %s: after OTP, Grant/Hub not seen (url=%s)", role, self.page.url)
                raise
            log.info("Login %s: after OTP, saw %s", role, _step_name(post_otp))
            if self._finish_if_hub_or_grant(post_otp):
                logged_in = True
                break
            if post_otp == NIH_AGREE:
                self.login_page.maybe_agree_nih_info_request()
                continue
            if post_otp == RULES_ACCEPT:
                self.login_page.maybe_accept_rules_of_use()
                continue
            if attempt < OTP_MAX_ATTEMPTS - 1:
                log.info("Login %s: Grant not ready, waiting 30s before OTP retry", role)
                self.page.wait_for_timeout(OTP_RETRY_WAIT_MS)

        if not logged_in:
            raise RuntimeError(f"OTP failed after {OTP_MAX_ATTEMPTS} attempts for role {role}")

        self.login_page.dismiss_system_use_warning(timeout_ms=3000)
        username = self.header.username(timeout_ms=20000)
        log.info("Login %s: Hub header username is %r", role, username)
        if not username_matches_role(username, role):
            raise RuntimeError(
                f"Login {role}: Hub header is {username!r}, not pbac.{role}-automation"
            )

    def _finish_if_hub_or_grant(self, step: str) -> bool:
        """True if this step completes Login.gov (Grant click or Hub already up)."""
        if step == GRANT:
            self.login_page.click_grant()
            return True
        if step == SYSTEM_USE_CONTINUE:
            self.login_page.dismiss_system_use_warning()
            return True
        return step == USERNAME

    def logout(self) -> None:
        if self.is_logged_in(timeout_ms=2000):
            self.header.logout()


def switch_user(hub: Hub, role: str) -> None:
    """Katalon switchUser: log out, drop SSO cookies (closeBrowser), Login.gov as role."""
    session = LoginSession(hub.page, hub.locators, hub.settings)
    session.logout()
    session._drop_browser_session()
    session.login_otp(role)
    if not session.signed_in_as(role):
        username = session.header.username(timeout_ms=5000) if session.is_logged_in() else ""
        raise RuntimeError(
            f"switch_user({role!r}) landed on Hub as {username!r}, not the requested role"
        )
    hub.role = role


def username_matches_role(username: str, role: str) -> bool:
    """True if header text is this PBAC automation user (PBAC.ADMIN-AUTOMATION, etc.)."""
    text = (username or "").lower()
    return f"pbac.{role.lower()}-automation" in text


def _step_name(path: str) -> str:
    names = {
        OTP: "OTP field",
        GRANT: "Grant button",
        NIH_AGREE: "NIH agree",
        RULES_ACCEPT: "Rules of Use",
        SYSTEM_USE_CONTINUE: "system use warning",
        USERNAME: "Hub username",
    }
    return names.get(path, path)
