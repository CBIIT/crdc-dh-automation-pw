"""Hub + Login.gov screens for the OTP login flow.

Locator constants are Katalon object-repository paths, not raw XPath.
.wait_for(state='visible') is Playwright auto-wait: it polls until the element
is shown or the timeout hits. Use a short timeout when the element is optional
(system-use banner, Rules of Use) so we do not sit for 8s when it is absent.
"""

from __future__ import annotations

import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage

SYSTEM_USE_CONTINUE = "CRDC/AILocators/Global/SystemUseWarning/Continue-Btn"
SYSTEM_USE_DIALOG = "CRDC/AILocators/Global/SystemUseWarning/Warning-Dialog"
LOGIN_PAGE_LOGIN_BTN = "CRDC/Login/LoginPageLogin-Btn"
LOGIN_DIALOG_LOGIN_BTN = "CRDC/AILocators/Home/LoginDialogLogin-Btn"
LOGIN_DIALOG_CLOSE_BTN = "CRDC/Login/LoginDialogClose-Btn"
LOGIN_GOV_BTN = "CRDC/Login/Login.gov-Btn"
EMAIL = "CRDC/Login/Login.gov_UserEmail-TxtBx"
PASSWORD = "CRDC/Login/Login.gov_UserPass-TxtBx"
SIGN_IN = "CRDC/Login/Login.gov_SignIn-Btn"
OTP = "CRDC/Login/Login.gov_OneTimeCode-TxtBx"
OTP_SUBMIT = "CRDC/Login/Login.gov_OneTimeCode_Submit-Btn"
GRANT = "CRDC/Login/Login.gov_ConsentGrant-Btn"
LOGIN_PAGE_CONTENT = "CRDC/AILocators/Login/LoginPageContent"
RULES_ACCEPT = "CRDC/AILocators/Login/RulesOfUseAccept-Chkbx"
RULES_SUBMIT = "CRDC/AILocators/Login/RulesOfUseSubmit-Btn"
NIH_AGREE = "CRDC/AILocators/Login/NihRequestingInfoAgreeSubmit-Btn"
# Same YAML path as HeaderPage.username_btn; wait_for_any returns this string.
USERNAME = "CRDC/AILocators/Global/Header/Desktop/UserName-Btn"

# After password, Login.gov may skip OTP and jump straight to Grant (slow Hub).
# After OTP, Grant may already have been clicked (OTP Submit landing on Grant after
# a page swap) and Hub is up — wait for Grant or a signed-in Hub chrome, not Grant only.
POST_PASSWORD_STEPS = (OTP, GRANT, NIH_AGREE, RULES_ACCEPT, SYSTEM_USE_CONTINUE, USERNAME)
POST_OTP_STEPS = (GRANT, NIH_AGREE, RULES_ACCEPT, SYSTEM_USE_CONTINUE, USERNAME)


class LoginPage(BasePage):
    def goto(self, base_url: str) -> None:
        """Open Hub (QA / QA2 / Stage). Does not wait for login to finish."""
        self.page.goto(base_url, wait_until="domcontentloaded")

    def _is_visible(self, path: str, timeout_ms: int) -> bool:
        try:
            self._loc(path).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    def dismiss_system_use_warning(self, timeout_ms: int = 1500) -> bool:
        """Click Continue if the banner shows, then wait until the dialog is gone.

        Cookie reuse often paints this after the header username, so callers should
        pass a few seconds. No-op if it never appears.
        """
        if not self._is_visible(SYSTEM_USE_CONTINUE, timeout_ms):
            return False
        self._loc(SYSTEM_USE_CONTINUE).first.click()
        try:
            self._loc(SYSTEM_USE_DIALOG).first.wait_for(state="hidden", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        return True

    def start_login_gov(self) -> None:
        """Hub Login button, then the Login.gov icon (NIH SSO).

        Logout from a protected page (Manage Users, etc.) leaves a modal
        ('Please log in to access User Management') over the header Login
        button. Click the dialog Login only when that modal is actually showing.
        After the click, NIH SSO may skip the Login.gov icon and land on email,
        Grant, or Hub — do not require the icon in those cases.
        """
        if self._protected_login_dialog_visible():
            self._loc(LOGIN_DIALOG_LOGIN_BTN).first.click()
        else:
            login_btn = self._loc(LOGIN_PAGE_LOGIN_BTN)
            login_btn.first.wait_for(state="visible", timeout=15000)
            login_btn.first.click()
        step = self.wait_for_any(
            (LOGIN_GOV_BTN, EMAIL, GRANT, SYSTEM_USE_CONTINUE, USERNAME),
            20000,
        )
        if step == LOGIN_GOV_BTN:
            self._loc(LOGIN_GOV_BTN).first.click()
        elif step == SYSTEM_USE_CONTINUE:
            self.dismiss_system_use_warning()

    def _protected_login_dialog_visible(self) -> bool:
        """True only if the login modal is on screen (close + Login), not the header button."""
        return self._is_visible(LOGIN_DIALOG_CLOSE_BTN, 800) and self._is_visible(
            LOGIN_DIALOG_LOGIN_BTN, 200
        )

    def submit_credentials(self, email: str, password: str) -> None:
        """Login.gov is sometimes email-then-password (two pages), sometimes both at once."""
        email_box = self._loc(EMAIL)
        email_box.first.wait_for(state="visible", timeout=20000)
        email_box.first.fill(email)
        pw = self._loc(PASSWORD)
        try:
            pw.first.wait_for(state="visible", timeout=3000)
        except PlaywrightTimeoutError:
            # Email-only page: Submit, then the password field appears.
            self._loc(SIGN_IN).first.click()
            pw.first.wait_for(state="visible", timeout=20000)
        pw.first.fill(password)
        self._loc(SIGN_IN).first.click()

    def visible_step(self, paths: tuple[str, ...]) -> str | None:
        """Which of these locators is on screen right now (no extra wait)."""
        for path in paths:
            if self._loc(path).first.is_visible():
                return path
        return None

    def wait_for_any(self, paths: tuple[str, ...], timeout_ms: int) -> str:
        """Wait until any of the locators is visible. Login.gov is slow and the next page varies.

        Grant can appear and vanish in the same beat (OTP Submit landing on Grant). Keep
        waiting through that flash so Hub username or the next Login.gov page can show.
        """
        xpaths = [self.locators.get(path) for path in paths]
        union = " | ".join(f"({xpath})" for xpath in xpaths)
        deadline = time.monotonic() + timeout_ms / 1000
        while True:
            found = self.visible_step(paths)
            if found:
                return found
            remaining_ms = int((deadline - time.monotonic()) * 1000)
            if remaining_ms <= 0:
                raise PlaywrightTimeoutError(
                    f"None of {paths} visible after {timeout_ms}ms (url={self.page.url})"
                )
            try:
                self.page.locator(union).first.wait_for(
                    state="visible", timeout=min(remaining_ms, 2000)
                )
            except PlaywrightTimeoutError:
                continue

    def maybe_accept_rules_of_use(self) -> bool:
        """Rare Login.gov page when terms change. No-op if it is not showing."""
        if not self._is_visible(RULES_ACCEPT, 1000) and not self._is_visible(LOGIN_PAGE_CONTENT, 500):
            return False
        content = self._loc(LOGIN_PAGE_CONTENT)
        try:
            text = content.first.inner_text(timeout=1000)
        except PlaywrightTimeoutError:
            text = ""
        if "Rules of Use" not in (text or "") and not self._loc(RULES_ACCEPT).first.is_visible():
            return False
        if self._loc(RULES_ACCEPT).first.is_visible():
            self._loc(RULES_ACCEPT).first.check()
            self._loc(RULES_SUBMIT).first.click()
            return True
        return False

    def maybe_agree_nih_info_request(self) -> bool:
        """Rare 'NIH is requesting new information' page."""
        if not self._is_visible(NIH_AGREE, 1000):
            return False
        self._loc(NIH_AGREE).first.click()
        return True

    def submit_otp(self, code: str) -> None:
        """Fill the six-digit TOTP. Click Submit only if Login.gov did not auto-advance."""
        otp_box = self._loc(OTP)
        otp_box.first.wait_for(state="visible", timeout=10000)
        otp_box.first.fill(code)
        # Login.gov often auto-submits a 6-digit code. If Submit is clicked after
        # the Grant page is already up, that click can land on Grant and Hub loads
        # while the keyword is still waiting for Grant.
        try:
            otp_box.first.wait_for(state="hidden", timeout=1500)
        except PlaywrightTimeoutError:
            self._loc(OTP_SUBMIT).first.click()

    def grant_visible(self, timeout_ms: int = 5000) -> bool:
        """True if the Login.gov Grant (OAuth consent) button is on screen."""
        return self._is_visible(GRANT, timeout_ms)

    def click_grant(self) -> None:
        """OAuth consent: send the code back to Hub and set the session cookie."""
        self._loc(GRANT).first.click()
