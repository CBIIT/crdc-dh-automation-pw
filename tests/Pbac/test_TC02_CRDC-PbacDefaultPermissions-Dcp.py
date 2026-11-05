"""Katalon: Test Cases/CRDC/Pbac/TC02_CRDC-PbacDefaultPermissions-Dcp

`hub` starts as Admin (fixture). Oracle: PBACPermissions.xlsx columns Dcp and Dcp-self.

Flow:
  1. Admin: reset pbac.Dcp-automation defaults, compare Dcp column
  2. Switch to Dcp (Login.gov OTP; new browser context)
  3. Profile: expand panels, compare Dcp-self column
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.users import ManageUsersPage
from crdc_pw.utils.pbac_helpers import (
    verify_role_defaults_as_admin,
    verify_self_defaults_on_profile,
)

log = logging.getLogger("crdc_pw.tc02_pbac")

pytestmark = pytest.mark.CRDC_PBAC


def test_TC02_CRDC_PbacDefaultPermissions_Dcp(hub: Hub) -> None:
    users = ManageUsersPage(hub)

    # Phase 1 — Admin on Manage Users (same pattern as TC01 Fedlead)
    verify_role_defaults_as_admin(hub, users, "Dcp")

    # Phase 2 — Data Commons Personnel views own Profile permissions
    switch_user(hub, "Dcp")
    verify_self_defaults_on_profile(hub, "Dcp-self")

    log.info("PASS TC02: Dcp default permissions as Admin and as self")
