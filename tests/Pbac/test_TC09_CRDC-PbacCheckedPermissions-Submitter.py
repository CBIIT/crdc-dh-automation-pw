"""Katalon: Test Cases/CRDC/Pbac/TC09_CRDC-PbacCheckedPermissions-Submitter

Flow:
  1. Admin: enable optional Submitter permissions and write the Submitter-positive sheet
  2. Switch to Submitter
  3. Verify functional handlers for checked permissions; skip notification keys
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.utils.pbac_helpers import edit_pbac_permissions, verify_permissions_functional

log = logging.getLogger("crdc_pw.tc09_pbac")

pytestmark = [pytest.mark.CRDC_PBAC, pytest.mark.CRDC_Regression, pytest.mark.CRDC_Smoke]


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC09_CRDC_PbacCheckedPermissions_Submitter(hub: Hub) -> None:
    # 1. Admin enables optional Submitter permissions and writes the positive oracle
    edit_pbac_permissions(hub, "Submitter", "positive")

    # 2. Continue as Submitter in a new browser context
    switch_user(hub, "Submitter")

    # 3. Check each selected functional permission as Submitter
    verify_permissions_functional(hub, "Submitter", "positive")

    log.info("PASS TC09: Submitter checked permissions (positive functional)")
