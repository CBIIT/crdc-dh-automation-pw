"""Hub chrome: the signed-in user menu in the desktop header."""

from __future__ import annotations

from crdc_pw.pages.base import BasePage

USERNAME = "CRDC/AILocators/Global/Header/Desktop/UserName-Btn"
LOGOUT = "CRDC/AILocators/Global/Header/Desktop/Logout-Btn"
MANAGE_STUDIES = "CRDC/AILocators/Global/Header/Desktop/ManageStudies-Link"
MANAGE_PROGRAMS = "CRDC/AILocators/Global/Header/Desktop/ManagePrograms-Link"


class HeaderPage(BasePage):
    def username_locator(self):
        return self.loc(USERNAME)

    def username(self, timeout_ms: int = 15000) -> str:
        """Wait until the header shows a name, then return that text."""
        loc = self.username_locator()
        loc.wait_for(state="visible", timeout=timeout_ms)
        return (loc.inner_text() or "").strip()

    def is_logged_in(self, timeout_ms: int = 5000) -> bool:
        """True if the username control appears before timeout. Used to skip Login.gov."""
        try:
            self.username_locator().wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False

    def logout(self) -> None:
        self.username_locator().click()
        self.loc(LOGOUT).click()
        self.username_locator().wait_for(state="hidden", timeout=15000)

    def open_user_menu(self) -> None:
        self.username_locator().click()

    def open_manage_studies(self) -> None:
        """User menu → Manage Studies. Katalon clickTab UserProfile-Dd then ManageStudies-Link."""
        self.open_user_menu()
        link = self.loc(MANAGE_STUDIES)
        link.wait_for(state="visible", timeout=10000)
        link.click()

    def open_manage_programs(self) -> None:
        """User menu → Manage Programs. Katalon clickTab UserProfile-Dd then ManagePrograms-Link."""
        self.open_user_menu()
        link = self.loc(MANAGE_PROGRAMS)
        link.wait_for(state="visible", timeout=10000)
        link.click()
