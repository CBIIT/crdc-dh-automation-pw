"""Katalon: Test Cases/CRDC/Pbac/TC06_CRDC-PbacCheckedPermissions-Fedlead

Admin enables all permissions for Fedlead (positive), writes Fedlead-positive sheet,
then Fedlead session verifies functional handlers for each checked key (others skipped).
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.utils.pbac_helpers import edit_pbac_permissions, verify_permissions_functional

log = logging.getLogger("crdc_pw.tc06_pbac")

pytestmark = pytest.mark.CRDC_PBAC


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC06_CRDC_PbacCheckedPermissions_Fedlead(hub: Hub) -> None:

    edit_pbac_permissions(hub, "Fedlead", "positive")
    switch_user(hub, "Fedlead")
    verify_permissions_functional(hub, "Fedlead", "positive")

    log.info("PASS TC06: Fedlead checked permissions (positive functional)")
