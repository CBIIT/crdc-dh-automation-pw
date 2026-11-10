"""Katalon: Test Cases/CRDC/Pbac/TC14_CRDC-PbacUncheckedPermissions-Submitter

Flow:
  1. Admin: uncheck optional Submitter permissions and write the Submitter-negative sheet
  2. Switch to Submitter
  3. Verify functional handlers are not accessible; skip notification keys

A standalone run leaves Submitter optional boxes unchecked. Restore with
EnableAllPermissions or a later positive (e.g. TC09) before smoke/positives.
Serial only (no -n). Shared PBAC users.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.utils.pbac_helpers import edit_pbac_permissions, verify_permissions_functional

log = logging.getLogger("crdc_pw.tc14_pbac")

pytestmark = [pytest.mark.CRDC_PBAC, pytest.mark.CRDC_Regression]


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC14_CRDC_PbacUncheckedPermissions_Submitter(hub: Hub) -> None:
    # 1. Admin unchecks optional Submitter permissions and writes the negative oracle
    edit_pbac_permissions(hub, "Submitter", "negative")

    # 2. Continue as Submitter in a new browser context
    switch_user(hub, "Submitter")

    # 3. Confirm each selected functional permission is not accessible as Submitter
    verify_permissions_functional(hub, "Submitter", "negative")

    log.info("PASS TC14: Submitter unchecked permissions (negative functional)")
