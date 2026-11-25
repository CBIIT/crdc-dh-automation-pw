"""Katalon: Test Cases/CRDC/SuiteSetup/EnableAllPermissions

Suite restore after PBAC default-compare tests: Master enables every optional permission
for pbac automation users (Admin, Dcp, Fedlead, Submitter, User). Not an Excel oracle.

Flow:
  1. Master → Manage Users
  2. For each role: reset to defaults, check all enabled boxes, Save
  3. Full `pytest -m CRDC_PBAC` runs TC01–TC05 then this test (conftest order); `-k TC01` skips restore.
  Requires MasterEmail / MasterPassword / MasterSecret in profile yaml. Run serial (no xdist).
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.users import ManageUsersPage

log = logging.getLogger("crdc_pw.enable_all_permissions")

pytestmark = pytest.mark.CRDC_PBAC

_ENABLE_ALL_ROLES = ("Admin", "Dcp", "Fedlead", "Submitter", "User")


@pytest.mark.parametrize("hub", ["Master"], indirect=True)
def test_EnableAllPermissions(hub: Hub) -> None:
    users = ManageUsersPage(hub)

    # 1. User menu → Manage Users
    users.open()

    # 2. Enable all optional permissions for each automation user (Katalon order)
    for role in _ENABLE_ALL_ROLES:
        log.info("EnableAllPermissions: processing role %s", role)
        users.enable_all_permissions(role)

    log.info("PASS EnableAllPermissions as %s", hub.role)
