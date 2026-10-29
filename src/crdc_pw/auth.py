"""Login.gov OTP login used by the hub fixture (not by tests).

Port of Katalon Login.loginToCrdcOtp: same screens and retry idea, Playwright waits
instead of WebUI.delay. After a successful Grant, Hub sets the connect.sid cookie.
"""

from __future__ import annotations

import logging
from pathlib import Path

from filelock import FileLock
from playwright.sync_api import Browser, BrowserContext, Page, ViewportSize
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.config import Settings
from crdc_pw.hub import Hub
from crdc_pw.locators.loader import LocatorLoader, repo_root
from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.login import (
    EMAIL,
    GRANT,
    NIH_AGREE,
    OTP,
    POST_OTP_STEPS,
    POST_PASSWORD_STEPS,
    RULES_ACCEPT,
    SYSTEM_USE_CONTINUE,
    SYSTEM_USE_DIALOG,
    USERNAME,
    LoginPage,
)
from crdc_pw.utils.otp import totp_now

log = logging.getLogger("crdc_pw.auth")

OTP_MAX_ATTEMPTS = 6  # Katalon used 6; TOTP changes every 30s
VIEWPORT: ViewportSize = {"width": 1920, "height": 1080}
_LOCK_TIMEOUT_S = 300
_validated: set[str] = set()
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
        """Open Hub base_url and dismiss the system-use banner if it is already up."""
        self.login_page.goto(self.settings.base_url)
        self.login_page.dismiss_system_use_warning()

    def is_logged_in(self, timeout_ms: int = 2000) -> bool:
        """True if the desktop header username is visible (Hub session, not Login.gov)."""
        return self.header.is_logged_in(timeout_ms=timeout_ms)

    def ensure_hub_ready(self, banner_appear_ms: int = 5000) -> None:
        """Dismiss the system-use banner if it paints after the header is up.

        Reused storage_state often shows the username first; tests then fail clicking
        it because the MUI dialog is on top. Call after login or session reuse.
        """
        if self.login_page.dismiss_system_use_warning(timeout_ms=banner_appear_ms):
            log.info("Dismissed system-use warning")

    def signed_in_as(self, role: str) -> bool:
        """True if Hub header is visible and the name is this PBAC automation user."""
        if not self.is_logged_in(timeout_ms=2000):
            return False
        try:
            username = self.header.username(timeout_ms=5000)
        except PlaywrightTimeoutError:
            return False
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
            if self.signed_in_as(role):
                log.info("Login %s: Hub after Login click (SSO session reuse)", role)
                return
        if self._finish_sso_without_email(role):
            self._confirm_hub_role(role)
            return
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

        self._confirm_hub_role(role)

    def _finish_sso_without_email(self, role: str) -> bool:
        """True if NIH SSO is already on Grant or Hub — do not wait for the email field."""
        try:
            step = self.login_page.wait_for_any(
                (EMAIL, GRANT, SYSTEM_USE_CONTINUE, USERNAME),
                20_000,
            )
        except PlaywrightTimeoutError:
            return False
        if step == EMAIL:
            return False
        log.info("Login %s: after Login click, saw %s (skipping credentials)", role, _step_name(step))
        return self._finish_if_hub_or_grant(step)

    def _confirm_hub_role(self, role: str) -> None:
        """Banner off, header is this PBAC automation user."""
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
        """Header Logout if a Hub session is up. No-op when already on Login.gov."""
        if self.is_logged_in(timeout_ms=2000):
            self.header.logout()


def storage_state_path(settings: Settings, role: str) -> Path:
    """auth/<profile>/<Role>.json (gitignored). Lock file sits next to it."""
    return repo_root() / "auth" / settings.profile / f"{role}.json"


def land_on_hub(page: Page, locators: LocatorLoader, settings: Settings) -> None:
    """goto Hub and dismiss the banner if it is up, without a 5s miss tax.

    Wait until Continue or the username is visible. Click Continue only when
    that is what appeared. Does not OTP.
    """
    login = LoginPage(page, locators)
    header = HeaderPage(page, locators)
    login.goto(settings.base_url)
    continue_btn = login._loc(SYSTEM_USE_CONTINUE).first
    username = header.username_btn
    # Both can be visible (banner on top of Hub). or_() without .first is strict-mode.
    continue_btn.or_(username).first.wait_for(state="visible")
    if continue_btn.is_visible():
        continue_btn.click()
        try:
            login._loc(SYSTEM_USE_DIALOG).first.wait_for(state="hidden", timeout=10_000)
        except PlaywrightTimeoutError:
            pass
        username.wait_for(state="visible")


def ensure_storage_state(
    browser: Browser,
    locators: LocatorLoader,
    settings: Settings,
    role: str,
    *,
    force: bool = False,
) -> Path:
    """File-locked: return a valid storage_state json, OTP-writing it if needed.

    The Hub header check runs once per role per worker, not once per test.
    Workers never OTP the same account at once (one lock file per role).
    """
    path = storage_state_path(settings, role)
    key = f"{settings.profile}:{role}"
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(path) + ".lock", timeout=_LOCK_TIMEOUT_S)
    with lock:
        if not force and key in _validated and path.is_file():
            return path
        if not force and path.is_file() and _storage_is_valid(browser, locators, settings, path, role):
            log.info("Login %s: saved session %s is valid", role, path.name)
            _validated.add(key)
            return path
        log.info("Login %s: Login.gov OTP to write %s", role, path.name)
        _otp_write_storage(browser, locators, settings, role, path)
        _validated.add(key)
        return path


def open_signed_in_page(
    browser: Browser,
    locators: LocatorLoader,
    settings: Settings,
    role: str,
) -> Page:
    """New context from storage_state, then land on Hub. One OTP retry if the cookie died."""
    path = ensure_storage_state(browser, locators, settings, role)
    context, page = _new_hub_context(browser, path)
    try:
        land_on_hub(page, locators, settings)
        return page
    except PlaywrightTimeoutError:
        context.close()
        path = ensure_storage_state(browser, locators, settings, role, force=True)
        context, page = _new_hub_context(browser, path)
        land_on_hub(page, locators, settings)
        return page


def switch_user(hub: Hub, role: str) -> None:
    """Katalon switchUser: new context from that role's storage_state (OTP only if missing)."""
    browser = hub.page.context.browser
    if browser is None:
        raise RuntimeError("switch_user: page has no browser")
    old = hub.page.context
    page = open_signed_in_page(browser, hub.locators, hub.settings, role)
    hub.page = page
    hub.role = role
    old.close()


def _new_hub_context(browser: Browser, path: Path) -> tuple[BrowserContext, Page]:
    context = browser.new_context(storage_state=str(path), viewport=VIEWPORT)
    context.set_default_timeout(BasePage.DEFAULT_MS)
    return context, context.new_page()


def _storage_is_valid(
    browser: Browser,
    locators: LocatorLoader,
    settings: Settings,
    path: Path,
    role: str,
) -> bool:
    context = browser.new_context(storage_state=str(path), viewport=VIEWPORT)
    context.set_default_timeout(BasePage.DEFAULT_MS)
    page = context.new_page()
    try:
        land_on_hub(page, locators, settings)
        username = HeaderPage(page, locators).username(timeout_ms=BasePage.PROBE_MS)
        return username_matches_role(username, role)
    except PlaywrightTimeoutError:
        return False
    finally:
        context.close()


def _otp_write_storage(
    browser: Browser,
    locators: LocatorLoader,
    settings: Settings,
    role: str,
    path: Path,
) -> None:
    context = browser.new_context(viewport=VIEWPORT)
    context.set_default_timeout(BasePage.DEFAULT_MS)
    page = context.new_page()
    try:
        LoginSession(page, locators, settings).login_otp(role)
        context.storage_state(path=str(path))
        log.info("Login %s: saved session to %s", role, path.name)
    finally:
        context.close()


def username_matches_role(username: str, role: str) -> bool:
    """True if header text is this PBAC automation user (PBAC.ADMIN-AUTOMATION, etc.)."""
    text = (username or "").lower()
    return f"pbac.{role.lower()}-automation" in text


def _step_name(path: str) -> str:
    """Locator path to a short label for login logs (OTP field, Grant button, ...)."""
    names = {
        OTP: "OTP field",
        GRANT: "Grant button",
        NIH_AGREE: "NIH agree",
        RULES_ACCEPT: "Rules of Use",
        SYSTEM_USE_CONTINUE: "system use warning",
        USERNAME: "Hub username",
    }
    return names.get(path, path)
