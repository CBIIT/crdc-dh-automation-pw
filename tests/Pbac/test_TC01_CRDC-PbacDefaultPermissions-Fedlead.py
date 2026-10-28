"""Katalon: Test Cases/CRDC/Pbac/TC01_CRDC-PbacDefaultPermissions-Fedlead

`hub` is already signed in as Admin (fixture). This file is the scenario after login.
PBACPermissions.xlsx is the expected driver (columns Fedlead and Fedlead-self).

Flow:
  1. Open Manage Users
  2. Reset pbac.Fedlead-automation to role defaults and compare checkboxes to the Fedlead column
  3. Switch to Fedlead
  4. Open Profile and compare checkboxes to the Fedlead-self column
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.users import ManageUsersPage, UserProfilePage
from crdc_pw.utils.pbac_sheet import compare_actual, output_path, write_expected

log = logging.getLogger("crdc_pw.tc01_pbac")

pytestmark = pytest.mark.CRDC_PBAC


def test_TC01_CRDC_PbacDefaultPermissions_Fedlead(hub: Hub) -> None:
    users = ManageUsersPage(hub.page, hub.locators)

    # 1. User menu → Manage Users
    users.open()

    # 2. Admin: find Fedlead automation user, reset to defaults, compare to sheet column Fedlead
    log.info("Logged in as: %r and verifying permissions for: Fedlead", hub.role)
    users.find_and_edit("Fedlead")
    users.reset_permissions("Fedlead")
    users.find_and_edit("Fedlead")
    users.expand_permission_panels()
    write_expected("Fedlead")
    fedlead_actual = users.read_permission_rows()
    fedlead_ok = compare_actual("Fedlead", fedlead_actual)
    assert fedlead_ok, f"Fedlead defaults mismatch; see {output_path()}"
    log.info("Assert PBAC: Fedlead defaults match PBACPermissions.xlsx")

    # 3. Logout and Login.gov as Fedlead (Katalon closeBrowser + loginToCrdcOtp)
    switch_user(hub, "Fedlead")

    # 4. Profile: Fedlead viewing self — compare to sheet column Fedlead-self (no search/reset)
    log.info("Logged in as: %r and verifying permissions for: Fedlead-self", hub.role)
    profile = UserProfilePage(hub.page, hub.locators)
    profile.open()
    profile.expand_permission_panels()
    write_expected("Fedlead-self")
    self_actual = profile.read_permission_rows()
    self_ok = compare_actual("Fedlead-self", self_actual)
    assert self_ok, f"Fedlead-self defaults mismatch; see {output_path()}"
    log.info("Assert PBAC: Fedlead-self defaults match PBACPermissions.xlsx")

    log.info("PASS TC01: Fedlead default permissions as Admin and as self")
