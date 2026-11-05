"""Katalon: Test Cases/CRDC/Pbac/TC04_CRDC-PbacDefaultPermissions-Submitter

Oracle: Submitter column on Manage Users only. Submitter-self is a negative check:
panels must not appear on Profile (Katalon does not sheet-compare Submitter-self here).

Flow:
  1. Admin: reset pbac.Submitter-automation defaults, compare Submitter column
  2. Switch to Submitter
  3. Profile: assert Permissions and Notifications panels absent
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.users import ManageUsersPage, UserProfilePage
from crdc_pw.utils.pbac_defaults import verify_role_defaults_as_admin

log = logging.getLogger("crdc_pw.tc04_pbac")

pytestmark = pytest.mark.CRDC_PBAC


def test_TC04_CRDC_PbacDefaultPermissions_Submitter(hub: Hub) -> None:
    users = ManageUsersPage(hub)

    # Phase 1 — Admin verifies Submitter default checkboxes on Manage Users
    verify_role_defaults_as_admin(hub, users, "Submitter")

    # Phase 2 — Submitter must not see PBAC UI on Profile (not verify_self_defaults_on_profile)
    switch_user(hub, "Submitter")
    log.info("Logged in as: %r and verifying permissions for: Submitter-self", hub.role)
    UserProfilePage(hub).assert_profile_permissions_not_visible("Submitter-self")

    log.info("PASS TC04: Submitter default permissions as Admin and restricted self profile")
