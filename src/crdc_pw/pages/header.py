"""Hub chrome: the signed-in user menu in the desktop header.

Used by list pages (open Manage Studies / Programs) and by the login fixture
(is the username visible yet?). Tests can also read username() after login.
"""

from __future__ import annotations

from crdc_pw.pages.base import BasePage

USERNAME = "CRDC/AILocators/Global/Header/Desktop/UserName-Btn"
LOGOUT = "CRDC/AILocators/Global/Header/Desktop/Logout-Btn"
MANAGE_STUDIES = "CRDC/AILocators/Global/Header/Desktop/ManageStudies-Link"
MANAGE_PROGRAMS = "CRDC/AILocators/Global/Header/Desktop/ManagePrograms-Link"
MANAGE_USERS = "CRDC/AILocators/Global/Header/Desktop/ManageUsers-Link"
USER_PROFILE = "CRDC/AILocators/Global/Header/Desktop/UserProfile-Link"


class HeaderPage(BasePage):
    def username_locator(self):
        """The clickable signed-in name in the desktop header."""
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
        """Open the user menu and click Logout; wait until the username is gone."""
        self.username_locator().click()
        self.loc(LOGOUT).click()
        self.username_locator().wait_for(state="hidden", timeout=15000)

    def open_user_menu(self) -> None:
        """Click the header username so Manage Studies / Programs / Logout appear."""
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

    def open_manage_users(self) -> None:
        """User menu → Manage Users. Katalon clickTab UserProfile-Dd then ManageUsers-Btn."""
        self.open_user_menu()
        link = self.loc(MANAGE_USERS)
        link.wait_for(state="visible", timeout=10000)
        link.click()

    def open_profile(self) -> None:
        """User menu → User Profile. Katalon clickTab UserProfile-Dd then UserProfile-Link."""
        self.open_user_menu()
        link = self.loc(USER_PROFILE)
        link.wait_for(state="visible", timeout=10000)
        link.click()
