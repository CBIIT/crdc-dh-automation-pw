"""Katalon: Test Cases/CRDC/Pbac/TC07_CRDC-PbacCheckedPermissions-Dcp

Flow:
  1. Admin: enable optional Dcp permissions and write the Dcp-positive sheet
  2. Switch to Dcp
  3. Verify functional handlers for checked permissions; skip notification keys
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.utils.pbac_helpers import edit_pbac_permissions, verify_permissions_functional

log = logging.getLogger("crdc_pw.tc07_pbac")

pytestmark = [pytest.mark.CRDC_PBAC, pytest.mark.CRDC_Regression]


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC07_CRDC_PbacCheckedPermissions_Dcp(hub: Hub) -> None:
    # 1. Admin enables optional Dcp permissions and writes the positive oracle
    edit_pbac_permissions(hub, "Dcp", "positive")

    # 2. Continue as Dcp in a new browser context
    switch_user(hub, "Dcp")

    # 3. Check each selected functional permission as Dcp
    verify_permissions_functional(hub, "Dcp", "positive")

    log.info("PASS TC07: Dcp checked permissions (positive functional)")
