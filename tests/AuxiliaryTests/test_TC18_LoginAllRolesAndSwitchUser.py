"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC18_LoginAllRolesAndSwitchUser

`app` is already signed in (fixture). This case only asserts we landed on Hub
as that role — there is no extra scenario after login.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.app import App
from crdc_pw.config import ROLES

log = logging.getLogger("crdc_pw.tc18")


@pytest.mark.smoke
@pytest.mark.parametrize("app", list(ROLES), indirect=True, ids=list(ROLES))
def test_TC18_LoginAllRolesAndSwitchUser(app: App) -> None:
    """One pytest case per role. Missing yaml values skip that role only."""
    username = app.header.username(timeout_ms=5000)
    url = app.page.url

    log.info("Assert %s: header username is non-empty (actual: %r)", app.role, username)
    assert username, f"{app.role}: expected a username in the Hub header after login"

    log.info("Assert %s: URL is Hub, not Login.gov (actual: %s)", app.role, url)
    assert "datacommons.cancer.gov" in url, f"{app.role}: expected Hub URL, got {url}"
    assert "login.gov" not in url.lower(), f"{app.role}: still on Login.gov ({url})"

    log.info("PASS %s: signed in as %r on %s", app.role, username, url)
