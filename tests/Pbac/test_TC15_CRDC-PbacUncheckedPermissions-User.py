"""Katalon: Test Cases/CRDC/Pbac/TC15_CRDC-PbacUncheckedPermissions-User

Flow:
  1. Admin: uncheck optional User permissions and write the User-negative sheet
  2. Switch to User
  3. Verify functional handlers are not accessible; skip notification keys

A standalone run leaves User optional boxes unchecked. Restore with
EnableAllPermissions or a later positive (e.g. TC10) before smoke/positives.
Serial only (no -n). Shared PBAC users.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.utils.pbac_helpers import edit_pbac_permissions, verify_permissions_functional

log = logging.getLogger("crdc_pw.tc15_pbac")

pytestmark = [pytest.mark.CRDC_PBAC, pytest.mark.CRDC_Regression]


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC15_CRDC_PbacUncheckedPermissions_User(hub: Hub) -> None:
    # 1. Admin unchecks optional User permissions and writes the negative oracle
    edit_pbac_permissions(hub, "User", "negative")

    # 2. Continue as User in a new browser context
    switch_user(hub, "User")

    # 3. Confirm each selected functional permission is not accessible as User
    verify_permissions_functional(hub, "User", "negative")

    log.info("PASS TC15: User unchecked permissions (negative functional)")
