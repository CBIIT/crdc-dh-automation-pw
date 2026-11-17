"""Katalon: Test Cases/CRDC/Pbac/TC11_CRDC-PbacUncheckedPermissions-Fedlead

Flow:
  1. Admin: uncheck optional Fedlead permissions and write the Fedlead-negative sheet
  2. Switch to Fedlead
  3. Verify functional handlers are not accessible; skip notification keys

A standalone run leaves Fedlead optional boxes unchecked. Restore with
EnableAllPermissions or a later positive (e.g. TC06) before smoke/positives.
Serial only (no -n). Shared PBAC users.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.utils.pbac_helpers import edit_pbac_permissions, verify_permissions_functional

log = logging.getLogger("crdc_pw.tc11_pbac")

pytestmark = [pytest.mark.CRDC_PBAC, pytest.mark.CRDC_Regression]


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC11_CRDC_PbacUncheckedPermissions_Fedlead(hub: Hub) -> None:
    # 1. Admin unchecks optional Fedlead permissions and writes the negative oracle
    edit_pbac_permissions(hub, "Fedlead", "negative")

    # 2. Continue as Fedlead in a new browser context
    switch_user(hub, "Fedlead")

    # 3. Confirm each selected functional permission is not accessible as Fedlead
    verify_permissions_functional(hub, "Fedlead", "negative")

    log.info("PASS TC11: Fedlead unchecked permissions (negative functional)")
