"""Manage Users list and the Edit User / Profile permission form.

Tests construct ManageUsersPage or UserProfilePage from hub, then:
  open()                   — header → Manage Users or Profile
  find_and_edit(role)      — filter/paginate to pbac.{role}-automation and click Edit
  reset_permissions(role)  — toggle Role away and back, Save (Katalon reset)
  expand_permission_panels()
  read_permission_rows()   — (label, status) for every PBAC checkbox

Locator constants are Katalon object-repository paths (YAML), not raw XPath.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Error, Locator
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.users")

CONTAINER = "CRDC/AILocators/Users/List/Container"
USER_FILTER = "CRDC/AILocators/Users/List/UserFilter-TxtBx"
GENERIC_ROW = "CRDC/AILocators/GenericTable/TableRow"
HTML_ROW = "CRDC/ManageUsers/ManageUsersTable-Row"
LOADING_ROW = "CRDC/AILocators/GenericTable/LoadingRow"
NEXT_PAGE = "CRDC/AILocators/GenericTable/Pagination/NextPage-Btn"
PERMISSIONS_PANEL = "CRDC/ManageUsers/PermissionsPanel-Ddn"
NOTIFICATIONS_PANEL = "CRDC/ManageUsers/NotificationsPanel-Ddn"
CHECKBOX = "CRDC/ManageUsers/PbacOptions-Chkbx"
CHECKBOX_LABEL = "CRDC/ManageUsers/PbacOptions-ChkbxLabel"
ROLE_DDN = "CRDC/ManageUsers/Role-Ddn"
ROLE_OPTION = "CRDC/ManageUsers/RoleDdn-Option"
SAVE = "CRDC/ManageUsers/Save-Btn"
SNACKBAR = "CRDC/AILocators/Global/Notistack-Snackbar"

ROLE_DISPLAY = {
    "User": "User",
    "Submitter": "Submitter",
    "Dcp": "Data Commons Personnel",
    "Fedlead": "Federal Lead",
    "Admin": "Admin",
}


class PermissionForm(BasePage):
    """Permissions + Notifications checkboxes on Edit User and on Profile."""

    def expand_permission_panels(self) -> None:
        """Open the Permissions and Email Notifications accordions."""
        self._loc(PERMISSIONS_PANEL).wait_for(state="visible")
        self._loc(PERMISSIONS_PANEL).click()
        self._loc(NOTIFICATIONS_PANEL).wait_for(state="visible")
        self._loc(NOTIFICATIONS_PANEL).click()

    def read_permission_rows(self) -> list[tuple[str, str]]:
        """Each PBAC checkbox as (display label, status). Order matches the sheet rows.

        Status is fixed_checked / fixed_unchecked / checked / unchecked, same as Katalon.
        """
        boxes = self._loc(CHECKBOX)
        labels = self._loc(CHECKBOX_LABEL)
        boxes.first.wait_for(state="attached")
        box_count = boxes.count()
        label_count = labels.count()
        if label_count != box_count:
            log.warning("label/checkbox count mismatch: labels=%s checkboxes=%s", label_count, box_count)
        rows: list[tuple[str, str]] = []
        for i in range(box_count):
            box = boxes.nth(i)
            label = labels.nth(i).inner_text().strip() if i < label_count else "MISSING_LABEL_UI"
            enabled = box.is_enabled()
            checked = box.is_checked()
            if not enabled and checked:
                status = "fixed_checked"
            elif not enabled and not checked:
                status = "fixed_unchecked"
            elif enabled and checked:
                status = "checked"
            elif enabled and not checked:
                status = "unchecked"
            else:
                status = "UNKNOWN"
            rows.append((label, status))
        return rows

    def reset_permissions(self, role: str) -> None:
        """Toggle Role to another value and back, then Save, so defaults reload."""
        display = ROLE_DISPLAY.get(role)
        if not display:
            raise ValueError(f"Invalid role passed to reset_permissions: {role}")
        alternate = next((name for name in ROLE_DISPLAY.values() if name != display), None)
        if not alternate:
            raise RuntimeError("Could not find alternate role to switch to.")
        log.info("Resetting permissions for role: %s (toggle away and back, then Save)", role)
        self._select_role(alternate)
        self._select_role(display)
        log.info("Role re-selected to %s; clicking Save", display)
        self._loc(SAVE).click()
        log.info("Clicked Save; waiting for snackbar")
        self._wait_for_snackbar_gone(self._loc(SNACKBAR))
        log.info("Save finished; snackbar gone")

    def _select_role(self, role_display: str) -> None:
        self._select_dropdown(
            self._loc(ROLE_DDN),
            self._loc(ROLE_OPTION, role=role_display),
        )
        log.info("Selected role: %s", role_display)


class ManageUsersPage(PermissionForm):
    def open(self) -> None:
        """User menu → Manage Users, then wait for the user table."""
        log.info("Navigate: Manage Users")
        HeaderPage(self.page, self.locators).open_manage_users()
        self._wait_for_table()
        log.info("Manage Users list page loaded")

    def find_and_edit(self, role: str) -> None:
        """Find pbac.{role}-automation in the table (filter, then paginate) and click Edit.

        Matches the token in any cell (Name is 'Please Do Not Edit, pbac.fedlead-automation',
        not column 0 when a checkbox column is present).
        """
        needle = f"pbac.{role}-automation"
        log.info("Find and Edit user %s", needle)
        self._wait_for_table()
        self._filter_user(needle)
        renav_attempted = False
        settled = True
        while True:
            if not settled:
                try:
                    self._wait_for_table()
                except PlaywrightTimeoutError:
                    if not renav_attempted:
                        renav_attempted = True
                        log.info("Manage Users table wait timed out; retrying after navigation.")
                        self.open()
                        self._wait_for_table()
                        self._filter_user(needle)
                    else:
                        raise
            settled = False
            if self._click_edit_on_current_page(needle):
                log.info("Clicked Edit for %r", needle)
                self._loc(ROLE_DDN).wait_for(state="visible")
                log.info("Edit form visible for %r", needle)
                return
            next_btn = self._loc(NEXT_PAGE).first
            if next_btn.is_disabled():
                raise RuntimeError(
                    f"Reached the last page. User '{needle}' not found in Manage Users table."
                )
            next_btn.click()
            settled = False

    def _filter_user(self, needle: str) -> None:
        """Type into the Name filter when Hub shows it. No-op if the box is missing."""
        box = self._loc(USER_FILTER)
        try:
            box.wait_for(state="visible", timeout=self.PROBE_MS)
        except PlaywrightTimeoutError:
            return
        try:
            current = (box.input_value() or "").strip()
        except Error:
            nested = box.locator("input").first
            current = (nested.input_value() or "").strip() if nested.count() else ""
        if current.lower() == needle.lower():
            log.info("Manage Users name filter already %r; skipping", needle)
            return
        log.info("Manage Users name filter: %r", needle)
        rows = self._table_rows()
        before = self._table_fingerprint(rows)
        box.fill(needle)
        self._wait_for_table_settled(self._loc(LOADING_ROW), rows, previous=before)

    def _click_edit_on_current_page(self, needle: str) -> bool:
        needle_l = needle.strip().lower()
        for row in self._table_rows().all():
            if needle_l not in (row.inner_text() or "").lower():
                continue
            edit = row.get_by_role("button", name="Edit")
            if edit.count() == 0:
                edit = row.locator("button").filter(has_text="Edit")
            if edit.count() == 0:
                continue
            edit.first.click()
            return True
        return False

    def _table_rows(self) -> Locator:
        generic = self._loc(GENERIC_ROW)
        if generic.count() > 0:
            return generic
        return self._loc(HTML_ROW)

    def _wait_for_table(self) -> None:
        self._loc(CONTAINER).wait_for(state="visible")
        self._loc(GENERIC_ROW).or_(self._loc(HTML_ROW)).first.wait_for(state="attached")
        self._wait_for_table_settled(self._loc(LOADING_ROW))


class UserProfilePage(PermissionForm):
    def open(self) -> None:
        """User menu → Profile, then wait for the permission form (or the page body)."""
        log.info("Navigate: User Profile")
        HeaderPage(self.page, self.locators).open_profile()
        self._loc(PERMISSIONS_PANEL).wait_for(state="visible")
        log.info("User Profile page loaded")
