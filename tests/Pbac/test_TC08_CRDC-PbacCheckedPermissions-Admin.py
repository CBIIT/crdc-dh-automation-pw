"""Katalon: Test Cases/CRDC/Pbac/TC08_CRDC-PbacCheckedPermissions-Admin

Flow:
  1. Admin: enable optional Admin permissions and write the Admin-positive sheet
  2. In the same Admin session, verify functional handlers for checked permissions
     and skip notification keys
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.utils.pbac_helpers import edit_pbac_permissions, verify_permissions_functional

log = logging.getLogger("crdc_pw.tc08_pbac")

pytestmark = [pytest.mark.CRDC_PBAC, pytest.mark.CRDC_Regression]


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC08_CRDC_PbacCheckedPermissions_Admin(hub: Hub) -> None:
    # 1. Admin enables own optional permissions and writes the positive oracle
    edit_pbac_permissions(hub, "Admin", "positive")

    # 2. Check each selected functional permission in the same Admin session
    verify_permissions_functional(hub, "Admin", "positive")

    log.info("PASS TC08: Admin checked permissions (positive functional)")
