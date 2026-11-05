"""PBAC default-permission oracles shared by TC01–TC05.

Mirrors Katalon Keywords/utilities/Pbac.groovy verifyPbacPermissionDefaults:
Admin phase (Manage Users reset + Excel compare) and self phase (Profile + sheet
column) for roles that expose PBAC panels on Profile. Submitter/User self checks
live in UserProfilePage.assert_profile_permissions_not_visible instead of here.
"""

from __future__ import annotations

import logging

from crdc_pw.hub import Hub
from crdc_pw.pages.users import ManageUsersPage, UserProfilePage
from crdc_pw.utils.pbac_sheet import compare_actual, output_path, write_expected

log = logging.getLogger("crdc_pw.pbac_defaults")


def verify_role_defaults_as_admin(hub: Hub, users: ManageUsersPage, role: str) -> None:
    """Phase 1: Admin resets automation user to role defaults and compares UI to Excel.

    Expects hub.role Admin and a ManageUsersPage bound to that session. Uses the
    column named ``role`` in InputFiles/CRDC/PBACPermissions.xlsx (e.g. Fedlead, Dcp).
    Writes row-level Pass/Fail to OutputFiles/PBAC_Defaults_Results.xlsx via pbac_sheet.
    """
    users.open()
    log.info("Logged in as: %r and verifying permissions for: %r", hub.role, role)
    # Katalon: find user, reset permissions (role toggle + Save), re-open edit form
    users.find_and_edit(role)
    users.reset_permissions(role)
    users.find_and_edit(role)
    users.expand_permission_panels()
    write_expected(role)
    actual = users.read_permission_rows()
    ok = compare_actual(role, actual)
    assert ok, f"{role} defaults mismatch; see {output_path()}"
    log.info("Assert PBAC: %s defaults match PBACPermissions.xlsx", role)


def verify_self_defaults_on_profile(hub: Hub, sheet_column: str) -> None:
    """Phase 2: signed-in role opens Profile and compares checkboxes to Excel *-self column.

    Used for Fedlead-self, Dcp-self, and Admin-self where PBAC panels are visible.
    Does not switch users; call switch_user before this when the case logs in as another role.
    """
    log.info("Logged in as: %r and verifying permissions for: %r", hub.role, sheet_column)
    profile = UserProfilePage(hub)
    profile.open()
    profile.expand_permission_panels()
    write_expected(sheet_column)
    actual = profile.read_permission_rows()
    ok = compare_actual(sheet_column, actual)
    assert ok, f"{sheet_column} defaults mismatch; see {output_path()}"
    log.info("Assert PBAC: %s defaults match PBACPermissions.xlsx", sheet_column)
