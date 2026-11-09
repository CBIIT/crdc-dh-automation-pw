"""Katalon: Test Cases/CRDC/Pbac/TC10_CRDC-PbacCheckedPermissions-User

Flow:
  1. Admin: enable optional User permissions and write the User-positive sheet
  2. Switch to User
  3. Verify functional handlers for checked permissions; skip notification keys
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.utils.pbac_helpers import edit_pbac_permissions, verify_permissions_functional

log = logging.getLogger("crdc_pw.tc10_pbac")

pytestmark = [pytest.mark.CRDC_PBAC, pytest.mark.CRDC_Regression]


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC10_CRDC_PbacCheckedPermissions_User(hub: Hub) -> None:
    # 1. Admin enables optional User permissions and writes the positive oracle
    edit_pbac_permissions(hub, "User", "positive")

    # 2. Continue as User in a new browser context
    switch_user(hub, "User")

    # 3. Check each selected functional permission as User
    verify_permissions_functional(hub, "User", "positive")

    log.info("PASS TC10: User checked permissions (positive functional)")
