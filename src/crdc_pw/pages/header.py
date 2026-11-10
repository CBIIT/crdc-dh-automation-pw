"""Hub chrome: the signed-in user menu in the desktop header.

Used by list pages (open Manage Studies / Programs / Data Submissions) and by
the login fixture (is the username visible yet?). Tests can also read
username() after login.
"""

from __future__ import annotations

from playwright.sync_api import Error, Locator
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage

_HOME_LOGO = "CRDC/NavBar/Home-Btn"
_USERNAME = "CRDC/AILocators/Global/Header/Desktop/UserName-Btn"
_LOGOUT = "CRDC/AILocators/Global/Header/Desktop/Logout-Btn"
_MANAGE_STUDIES = "CRDC/AILocators/Global/Header/Desktop/ManageStudies-Link"
_MANAGE_PROGRAMS = "CRDC/AILocators/Global/Header/Desktop/ManagePrograms-Link"
_MANAGE_INSTITUTIONS = "CRDC/AILocators/Global/Header/Desktop/ManageInstitutions-Link"
_MANAGE_USERS = "CRDC/AILocators/Global/Header/Desktop/ManageUsers-Link"
_OPERATION_DASHBOARD = "CRDC/AILocators/Global/Header/Desktop/OperationDashboard-Link"
_USER_PROFILE = "CRDC/AILocators/Global/Header/Desktop/UserProfile-Link"
_DATA_SUBMISSIONS = "CRDC/AILocators/Global/Header/Desktop/DataSubmissions-Tab"
_DATA_EXPLORER = "CRDC/AILocators/Global/Header/Desktop/DataExplorer-Tab"
_SUBMISSION_REQUESTS = "CRDC/AILocators/Global/Header/Desktop/SubmissionRequests-Tab"
_API_TOKEN = "CRDC/AILocators/Global/Header/Desktop/APIToken-Btn"


class HeaderPage(BasePage):
    def go_home(self) -> None:
        """Click the header logo to return home (Katalon SubmissionRequest.clickHome)."""
        btn = self._loc(_HOME_LOGO)
        btn.wait_for(state="visible")
        btn.click()

    @property
    def username_btn(self) -> Locator:
        """The clickable signed-in name in the desktop header."""
        return self._loc(_USERNAME)

    def username(self, timeout_ms: int | None = None) -> str:
        """Wait until the header shows a name, then return that text."""
        if timeout_ms is None:
            self.username_btn.wait_for(state="visible")
        else:
            self.username_btn.wait_for(state="visible", timeout=timeout_ms)
        return (self.username_btn.inner_text() or "").strip()

    def is_logged_in(self, timeout_ms: int | None = None) -> bool:
        """True if the username control appears before timeout. Used to skip Login.gov."""
        if timeout_ms is None:
            timeout_ms = self.PROBE_MS
        try:
            self.username_btn.wait_for(state="visible", timeout=timeout_ms)
            return True
        except (PlaywrightTimeoutError, Error):
            return False

    def logout(self) -> None:
        """Open the user menu and click Logout; wait until the username is gone."""
        self.username_btn.click()
        self._loc(_LOGOUT).click()
        self.username_btn.wait_for(state="hidden")

    def open_user_menu(self) -> None:
        """Click the header username so Manage Studies / Programs / Logout appear."""
        self.username_btn.click()

    def open_manage_studies(self) -> None:
        """User menu → Manage Studies. Katalon clickTab UserProfile-Dd then ManageStudies-Link."""
        self.open_user_menu()
        link = self._loc(_MANAGE_STUDIES)
        link.wait_for(state="visible")
        link.click()

    def open_manage_programs(self) -> None:
        """User menu → Manage Programs. Katalon clickTab UserProfile-Dd then ManagePrograms-Link."""
        self.open_user_menu()
        link = self._loc(_MANAGE_PROGRAMS)
        link.wait_for(state="visible")
        link.click()

    def open_manage_users(self) -> None:
        """User menu → Manage Users. Katalon clickTab UserProfile-Dd then ManageUsers-Btn."""
        self.open_user_menu()
        link = self._loc(_MANAGE_USERS)
        link.wait_for(state="visible")
        link.click()

    def open_profile(self) -> None:
        """User menu → User Profile. Katalon clickTab UserProfile-Dd then UserProfile-Link."""
        self.open_user_menu()
        link = self._loc(_USER_PROFILE)
        link.wait_for(state="visible")
        link.click()

    def open_data_submissions(self) -> None:
        """Nav bar Data Submissions. Katalon clickTab DataSubmissions-Tab."""
        tab = self._loc(_DATA_SUBMISSIONS)
        tab.wait_for(state="visible")
        tab.click()

    def open_data_explorer(self) -> None:
        """User menu → Data Explorer. Katalon clickTab DataExplorer-Tab (under user dropdown)."""
        self.open_user_menu()
        tab = self._loc(_DATA_EXPLORER)
        tab.wait_for(state="visible")
        tab.click()

    def open_submission_requests(self) -> None:
        """Nav bar Submission Requests. Katalon clickTab SubmissionRequest-Tab."""
        tab = self._loc(_SUBMISSION_REQUESTS)
        tab.wait_for(state="visible")
        tab.click()

    def is_api_token_button_visible(self) -> bool:
        """True if API Token appears in the open user menu (PBAC ``data_submission:create``).

        Call ``open_user_menu()`` first so dropdown entries are visible.
        """
        return self._loc(_API_TOKEN).first.is_visible()

    def is_nav_manage_programs_visible(self) -> bool:
        """User menu open — Manage Programs in dropdown (PBAC ``program:manage``)."""
        return self._loc(_MANAGE_PROGRAMS).first.is_visible()

    def is_nav_manage_studies_visible(self) -> bool:
        """User menu open — Manage Studies in dropdown (PBAC ``study:manage``)."""
        return self._loc(_MANAGE_STUDIES).first.is_visible()

    def is_nav_manage_institutions_visible(self) -> bool:
        """User menu open — Manage Institutions in dropdown (PBAC ``institution:manage``)."""
        return self._loc(_MANAGE_INSTITUTIONS).first.is_visible()

    def is_nav_manage_users_visible(self) -> bool:
        """User menu open — Manage Users in dropdown (PBAC ``user:manage``)."""
        return self._loc(_MANAGE_USERS).first.is_visible()

    def is_nav_operation_dashboard_visible(self) -> bool:
        """User menu open — Operation Dashboard in dropdown (PBAC ``dashboard:view``)."""
        return self._loc(_OPERATION_DASHBOARD).first.is_visible()
