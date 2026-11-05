"""Katalon: Test Cases/CRDC/Pbac/TC01_CRDC-PbacDefaultPermissions-Fedlead

`hub` is already signed in as Admin (fixture). PBACPermissions.xlsx columns Fedlead and Fedlead-self.

Flow:
  1. Admin: reset pbac.Fedlead-automation defaults, compare Fedlead column
  2. Switch to Fedlead
  3. Profile: compare Fedlead-self column
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.users import ManageUsersPage
from crdc_pw.utils.pbac_defaults import (
    verify_role_defaults_as_admin,
    verify_self_defaults_on_profile,
)

log = logging.getLogger("crdc_pw.tc01_pbac")

pytestmark = pytest.mark.CRDC_PBAC


def test_TC01_CRDC_PbacDefaultPermissions_Fedlead(hub: Hub) -> None:
    users = ManageUsersPage(hub)

    # Phase 1 — Admin: reset pbac.Fedlead-automation, compare Fedlead column
    verify_role_defaults_as_admin(hub, users, "Fedlead")

    # Phase 2 — Federal Lead self view (Katalon closeBrowser + loginToCrdcOtp)
    switch_user(hub, "Fedlead")
    verify_self_defaults_on_profile(hub, "Fedlead-self")

    log.info("PASS TC01: Fedlead default permissions as Admin and as self")
