"""Katalon: Test Cases/CRDC/Pbac/TC03_CRDC-PbacDefaultPermissions-Admin

`hub` stays Admin for both phases. Oracle: Admin and Admin-self columns.

Flow:
  1. Admin: reset pbac.Admin-automation defaults, compare Admin column
  2. Profile as Admin: compare Admin-self (no switch; no reset on Profile)
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.users import ManageUsersPage
from crdc_pw.utils.pbac_defaults import (
    verify_role_defaults_as_admin,
    verify_self_defaults_on_profile,
)

log = logging.getLogger("crdc_pw.tc03_pbac")

pytestmark = pytest.mark.CRDC_PBAC


def test_TC03_CRDC_PbacDefaultPermissions_Admin(hub: Hub) -> None:
    users = ManageUsersPage(hub)

    # Phase 1 — Admin edits own automation user on Manage Users
    verify_role_defaults_as_admin(hub, users, "Admin")

    # Phase 2 — same session: User menu → Profile (Katalon does not switch role)
    verify_self_defaults_on_profile(hub, "Admin-self")

    log.info("PASS TC03: Admin default permissions as Admin and as self")
