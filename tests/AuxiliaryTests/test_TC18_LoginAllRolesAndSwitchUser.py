"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC18_LoginAllRolesAndSwitchUser

`hub` is already signed in (fixture). This case only asserts we landed on Hub
as that role — there is no extra scenario after login.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.config import ROLES
from crdc_pw.hub import Hub
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.tc18")


@pytest.mark.smoke
@pytest.mark.parametrize("hub", list(ROLES), indirect=True, ids=list(ROLES))
def test_TC18_LoginAllRolesAndSwitchUser(hub: Hub) -> None:
    """One pytest case per role. Missing yaml values skip that role only."""
    header = HeaderPage(hub.page, hub.locators)
    username = header.username(timeout_ms=5000)
    url = hub.page.url

    log.info("Assert %s: header username is non-empty (actual: %r)", hub.role, username)
    assert username, f"{hub.role}: expected a username in the Hub header after login"

    log.info("Assert %s: URL is Hub, not Login.gov (actual: %s)", hub.role, url)
    assert "datacommons.cancer.gov" in url, f"{hub.role}: expected Hub URL, got {url}"
    assert "login.gov" not in url.lower(), f"{hub.role}: still on Login.gov ({url})"

    log.info("PASS %s: signed in as %r on %s", hub.role, username, url)
