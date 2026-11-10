"""Katalon: Test Cases/CRDC/Pbac/TC12_CRDC-PbacUncheckedPermissions-Dcp

Flow:
  1. Admin: uncheck optional Dcp permissions and write the Dcp-negative sheet
  2. Switch to Dcp
  3. Verify functional handlers are not accessible; skip notification keys

A standalone run leaves Dcp optional boxes unchecked. Restore with
EnableAllPermissions or a later positive (e.g. TC07) before smoke/positives.
Serial only (no -n). Shared PBAC users.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.utils.pbac_helpers import edit_pbac_permissions, verify_permissions_functional

log = logging.getLogger("crdc_pw.tc12_pbac")

pytestmark = [pytest.mark.CRDC_PBAC, pytest.mark.CRDC_Regression]


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC12_CRDC_PbacUncheckedPermissions_Dcp(hub: Hub) -> None:
    # 1. Admin unchecks optional Dcp permissions and writes the negative oracle
    edit_pbac_permissions(hub, "Dcp", "negative")

    # 2. Continue as Dcp in a new browser context
    switch_user(hub, "Dcp")

    # 3. Confirm each selected functional permission is not accessible as Dcp
    verify_permissions_functional(hub, "Dcp", "negative")

    log.info("PASS TC12: Dcp unchecked permissions (negative functional)")
