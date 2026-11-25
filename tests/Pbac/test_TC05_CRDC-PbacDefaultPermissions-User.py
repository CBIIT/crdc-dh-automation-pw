"""Katalon: Test Cases/CRDC/Pbac/TC05_CRDC-PbacDefaultPermissions-User

Oracle: User column on Manage Users only. User-self is a negative Profile check
(same branch as TC04 Submitter-self in verifyPbacPermissionDefaults).

Flow:
  1. Admin: reset pbac.User-automation defaults, compare User column
  2. Switch to User
  3. Profile: assert Permissions and Notifications panels absent
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.users import ManageUsersPage, UserProfilePage
from crdc_pw.utils.pbac_helpers import verify_role_defaults_as_admin

log = logging.getLogger("crdc_pw.tc05_pbac")

pytestmark = pytest.mark.CRDC_PBAC


def test_TC05_CRDC_PbacDefaultPermissions_User(hub: Hub) -> None:
    users = ManageUsersPage(hub)

    # Phase 1 — Admin verifies User default checkboxes on Manage Users
    verify_role_defaults_as_admin(hub, users, "User")

    # Phase 2 — User must not see PBAC panels on Profile
    switch_user(hub, "User")
    log.info("Logged in as: %r and verifying permissions for: User-self", hub.role)
    UserProfilePage(hub).assert_profile_permissions_not_visible("User-self")

    log.info("PASS TC05: User default permissions as Admin and restricted self profile")
