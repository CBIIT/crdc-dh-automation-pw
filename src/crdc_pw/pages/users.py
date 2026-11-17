"""Manage Users list and the Edit User / Profile permission form.

Tests construct ManageUsersPage or UserProfilePage from hub, then:
  open()                   — header → Manage Users or Profile
  find_and_edit(role)      — filter/paginate to pbac.{role}-automation and click Edit
  reset_permissions(role)  — toggle Role away and back, Save (Katalon reset)
  expand_permission_panels()
  read_permission_rows()   — (label, status) for every PBAC checkbox
  check_all_enabled_permission_checkboxes() — positive EnableAll (Katalon checkAllEnabled…)
  uncheck_all_enabled_permission_checkboxes() — negative uncheck-all (Katalon uncheckAllEnabled…)
  apply_positive_permission_edit / apply_negative_permission_edit — ManageUsersPage only
  enable_all_permissions(role) — on ManageUsersPage only (Katalon editPbacPermissions positive)

Locator constants are Katalon object-repository paths (YAML), not raw XPath.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Error, Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.users")

CONTAINER = "CRDC/AILocators/Users/List/Container"
USER_FILTER = "CRDC/AILocators/Users/List/UserFilter-TxtBx"
GENERIC_ROW = "CRDC/AILocators/GenericTable/TableRow"
HTML_ROW = "CRDC/ManageUsers/ManageUsersTable-Row"
NEXT_PAGE = "CRDC/AILocators/GenericTable/Pagination/NextPage-Btn"
PERMISSIONS_PANEL = "CRDC/ManageUsers/PermissionsPanel-Ddn"
NOTIFICATIONS_PANEL = "CRDC/ManageUsers/NotificationsPanel-Ddn"
CHECKBOX = "CRDC/ManageUsers/PbacOptions-Chkbx"
CHECKBOX_LABEL = "CRDC/ManageUsers/PbacOptions-ChkbxLabel"
ROLE_DDN = "CRDC/ManageUsers/Role-Ddn"
ROLE_OPTION = "CRDC/ManageUsers/RoleDdn-Option"
SAVE = "CRDC/ManageUsers/Save-Btn"
REQUEST_ACCESS = "CRDC/ManageUsers/RequestAccess-Btn"
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
        self._wait_for_permissions_hydrated()
        log.info("Role re-selected to %s; clicking Save", display)
        self._loc(SAVE).click()
        log.info("Clicked Save; waiting for snackbar")
        self._wait_for_snackbar_gone(self._loc(SNACKBAR))
        self._loc(CONTAINER).wait_for(state="visible")
        log.info("Save finished; Manage Users list visible")

    def _wait_for_permissions_hydrated(self) -> None:
        """After a Role change, wait until the Permissions accordion is not still (0).

        Katalon delay(2) after re-selecting the role before Save. Saving while the
        header still shows Permissions (0) does not return to the Manage Users list.
        """
        panel = self._loc(PERMISSIONS_PANEL)
        panel.wait_for(state="visible")
        expect(panel).not_to_contain_text("(0)", timeout=self.DEFAULT_MS)
        log.info("Permissions accordion hydrated after role select")

    def _select_role(self, role_display: str) -> None:
        self._select_dropdown(
            self._loc(ROLE_DDN),
            self._loc(ROLE_OPTION, role=role_display),
        )
        log.info("Selected role: %s", role_display)

    def check_all_enabled_permission_checkboxes(self) -> None:
        """Check every enabled PBAC checkbox that is not already checked (Katalon positive scenario)."""
        snackbar = self._loc(SNACKBAR)
        self._wait_for_snackbar_gone(snackbar)
        boxes = self._loc(CHECKBOX)
        boxes.first.wait_for(state="attached")
        for i in range(boxes.count()):
            box = boxes.nth(i)
            if not box.is_enabled() or box.is_checked():
                continue
            self._check_permission_box(box, snackbar)

    def _check_permission_box(self, box: Locator, snackbar: Locator) -> None:
        try:
            box.check()
            log.info("Checked permission checkbox")
        except Error as exc:
            log.info("Checkbox check failed (likely Notistack); waiting and retrying once: %s", exc)
            self._wait_for_snackbar_gone(snackbar)
            box.check()
            log.info("Checked permission checkbox after retry")

    def uncheck_all_enabled_permission_checkboxes(self) -> None:
        """Uncheck every enabled PBAC checkbox that is checked (Katalon negative scenario).

        One pass only. Call twice from apply_negative_permission_edit so DCP SR View
        can be unchecked after higher boxes unlock it.
        """
        snackbar = self._loc(SNACKBAR)
        self._wait_for_snackbar_gone(snackbar)
        boxes = self._loc(CHECKBOX)
        boxes.first.wait_for(state="attached")
        for i in range(boxes.count()):
            box = boxes.nth(i)
            if not box.is_enabled() or not box.is_checked():
                continue
            self._uncheck_permission_box(box, snackbar)

    def _uncheck_permission_box(self, box: Locator, snackbar: Locator) -> None:
        try:
            box.uncheck()
            log.info("Unchecked permission checkbox")
        except Error as exc:
            log.info("Checkbox uncheck failed (likely Notistack); waiting and retrying once: %s", exc)
            self._wait_for_snackbar_gone(snackbar)
            box.uncheck()
            log.info("Unchecked permission checkbox after retry")


class ManageUsersPage(PermissionForm):
    def open(self) -> None:
        """User menu → Manage Users, then wait for the user table."""
        log.info("Navigate: Manage Users")
        HeaderPage(self._hub).open_manage_users()
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
        self.wait_for_generic_table_settled(rows, previous=before)

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
        self.wait_for_generic_table_settled()

    def apply_positive_permission_edit(self, role: str) -> None:
        """Katalon editPbacPermissions(role, 'positive') UI only — reset, check all enabled, Save."""
        if role not in ROLE_DISPLAY:
            raise ValueError(f"Invalid role passed to apply_positive_permission_edit: {role}")
        log.info("Positive permission edit for role: %s", role)
        self.find_and_edit(role)
        self.reset_permissions(role)
        self.find_and_edit(role)
        self.expand_permission_panels()
        self.check_all_enabled_permission_checkboxes()
        self._loc(SAVE).click()
        log.info("Clicked Save after positive permission edit for %s", role)
        self._wait_for_snackbar_gone(self._loc(SNACKBAR))
        self._loc(CONTAINER).wait_for(state="visible")
        log.info("Positive permission edit finished for %s", role)

    def apply_negative_permission_edit(self, role: str) -> None:
        """Katalon editPbacPermissions(role, 'negative') UI only — reset, uncheck twice, Save.

        Second uncheck pass is for DCP SR View, which stays disabled until higher boxes
        are cleared.
        """
        if role not in ROLE_DISPLAY:
            raise ValueError(f"Invalid role passed to apply_negative_permission_edit: {role}")
        log.info("Negative permission edit for role: %s", role)
        self.find_and_edit(role)
        self.reset_permissions(role)
        self.find_and_edit(role)
        self.expand_permission_panels()
        self.uncheck_all_enabled_permission_checkboxes()
        self.uncheck_all_enabled_permission_checkboxes()
        self._loc(SAVE).click()
        log.info("Clicked Save after negative permission edit for %s", role)
        self._wait_for_snackbar_gone(self._loc(SNACKBAR))
        self._loc(CONTAINER).wait_for(state="visible")
        log.info("Negative permission edit finished for %s", role)

    def enable_all_permissions(self, role: str) -> None:
        """Katalon editPbacPermissions(role, 'positive') without Excel — reset then check all enabled."""
        log.info("Enable all permissions for role: %s", role)
        self.apply_positive_permission_edit(role)
        log.info("Enable all permissions finished for %s", role)


class UserProfilePage(PermissionForm):
    def open(self) -> None:
        """User menu → Profile, then wait for the permission form (Fedlead/Dcp/Admin-self)."""
        log.info("Navigate: User Profile")
        HeaderPage(self._hub).open_profile()
        self._loc(PERMISSIONS_PANEL).wait_for(state="visible")
        log.info("User Profile page loaded")

    def open_profile_menu_only(self) -> None:
        """Open Profile without waiting for PBAC panels (restricted self roles).

        Prefer UserProfilePage.open when panels must be visible for sheet compare
        (Fedlead/Dcp/Admin-self). Submitter and User must not see Permissions or
        Notifications dropdowns on Profile; waiting on PERMISSIONS_PANEL would timeout.
        """
        log.info("Navigate: User Profile (no PBAC panels expected)")
        HeaderPage(self._hub).open_profile()

    def is_request_access_button_visible(self) -> bool:
        """Wait up to the Hub timeout for Request Access on Profile; return False on timeout.

        Profile must already be open (e.g. ``HeaderPage.open_profile()``).
        """
        try:
            self._loc(REQUEST_ACCESS).first.wait_for(state="visible", timeout=self.DEFAULT_MS)
        except PlaywrightTimeoutError:
            log.info("Request Access did not become visible within %s ms", self.DEFAULT_MS)
            return False
        return True

    def assert_profile_permissions_not_visible(self, role_self: str) -> None:
        """Assert Submitter-self / User-self: no PBAC panels on Profile (Katalon TC04/TC05).

        role_self is only used in Pass/Fail log text (e.g. Submitter-self). Excel
        Submitter-self / User-self columns are not compared when panels are absent.
        """
        self.open_profile_menu_only()
        probe_ms = self.PROBE_MS
        # Brief settle; Katalon uses optional ~5s presence check, not DEFAULT_MS wait
        self.page.wait_for_timeout(probe_ms)
        perm_present = self._pbac_panel_present(self._loc(PERMISSIONS_PANEL), probe_ms)
        notif_present = self._pbac_panel_present(self._loc(NOTIFICATIONS_PANEL), probe_ms)
        if perm_present or notif_present:
            raise AssertionError(
                f"FAIL -- {role_self} is able to see permissions in profile"
            )
        log.info("PASS -- %s is not able to view permissions in profile", role_self)

    @staticmethod
    def _pbac_panel_present(panel: Locator, timeout_ms: int) -> bool:
        """Return True if a Permissions/Notifications panel becomes visible within probe_ms."""
        try:
            panel.first.wait_for(state="visible", timeout=timeout_ms)
            return panel.first.is_visible()
        except (PlaywrightTimeoutError, Error):
            try:
                return panel.first.is_visible()
            except Error:
                return False
