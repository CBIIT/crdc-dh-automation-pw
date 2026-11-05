"""PBAC suite orchestration (Katalon utilities/Pbac.groovy).

Home for multi-step PBAC flows that span pages: default permission compares
(TC01–TC05 today), and later edit positive/negative and functional permission
maps. DOM actions stay on ManageUsersPage / UserProfilePage (and SR/DS pages);
Excel oracles stay in pbac_sheet.py.
"""

from __future__ import annotations

import logging

from crdc_pw.hub import Hub
from crdc_pw.pages.users import ManageUsersPage, UserProfilePage
from crdc_pw.utils.pbac_sheet import compare_actual, output_path, write_expected

log = logging.getLogger("crdc_pw.pbac_helpers")


def verify_role_defaults_as_admin(hub: Hub, users: ManageUsersPage, role: str) -> None:
    """Phase 1: Admin resets automation user to role defaults and compares UI to Excel.

    Mirrors verifyPbacPermissionDefaults admin branch. Expects hub.role Admin.
    Uses the column named ``role`` in InputFiles/CRDC/PBACPermissions.xlsx.
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
    Submitter-self / User-self use UserProfilePage.assert_profile_permissions_not_visible.
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
