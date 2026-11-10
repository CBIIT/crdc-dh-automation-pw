"""Katalon: Test Cases/CRDC/Pbac/TC13_CRDC-PbacUncheckedPermissions-Admin

Flow:
  1. Master: uncheck optional Admin permissions and write the Admin-negative sheet
  2. Switch to Admin and verify functional handlers are not accessible
  3. Switch back to Master and restore Admin positive (Manage Users still works)

Do not start as Admin (TC08 self-edit). Unchecking Admin as Admin would remove
Manage Users. Restore is inside this test (try/finally) so a verify FAIL still
leaves Admin usable. EnableAllPermissions remains the suite restore for other
roles. Serial only (no -n). Shared PBAC users. Needs Master credentials.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.utils.pbac_helpers import edit_pbac_permissions, verify_permissions_functional

log = logging.getLogger("crdc_pw.tc13_pbac")

pytestmark = [pytest.mark.CRDC_PBAC, pytest.mark.CRDC_Regression]


@pytest.mark.parametrize("hub", ["Master"], indirect=True)
def test_TC13_CRDC_PbacUncheckedPermissions_Admin(hub: Hub) -> None:
    # 1. Master unchecks optional Admin permissions and writes the negative oracle
    edit_pbac_permissions(hub, "Admin", "negative")
    try:
        # 2. Continue as Admin and confirm selected functional permissions are not accessible
        switch_user(hub, "Admin")
        verify_permissions_functional(hub, "Admin", "negative")
    finally:
        # 3. Master restores Admin positive so Manage Users still works
        switch_user(hub, "Master")
        edit_pbac_permissions(hub, "Admin", "positive")

    log.info("PASS TC13: Admin unchecked permissions (negative functional); Admin restored")
