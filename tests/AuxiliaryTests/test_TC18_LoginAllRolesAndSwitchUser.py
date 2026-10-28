"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC18_LoginAllRolesAndSwitchUser

`hub` is already signed in as this role (fixture). No list/filter scenario after login.

Runs once per role: Admin, Fedlead, Dcp, Submitter, User, Master.
A role with blank yaml credentials is skipped, not failed.

Flow:
  1. Read the header username
  2. Assert we are on Hub, not still on Login.gov
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.config import ROLES
from crdc_pw.hub import Hub
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.tc18")

pytestmark = pytest.mark.CRDC_Auxiliary


@pytest.mark.parametrize("hub", list(ROLES), indirect=True, ids=list(ROLES))
def test_TC18_LoginAllRolesAndSwitchUser(hub: Hub) -> None:
    """One pytest case per role. Missing yaml values skip that role only."""
    header = HeaderPage(hub.page, hub.locators)

    # 1. Signed-in name in the desktop header (empty means login did not finish)
    username = header.username(timeout_ms=5000)
    url = hub.page.url

    log.info("Assert %s: header username is non-empty (actual: %r)", hub.role, username)
    assert username, f"{hub.role}: expected a username in the Hub header after login"

    # 2. URL is Data Commons Hub, not login.gov
    log.info("Assert %s: URL is Hub, not Login.gov (actual: %s)", hub.role, url)
    assert "datacommons.cancer.gov" in url, f"{hub.role}: expected Hub URL, got {url}"
    assert "login.gov" not in url.lower(), f"{hub.role}: still on Login.gov ({url})"

    log.info("PASS %s: signed in as %r on %s", hub.role, username, url)
