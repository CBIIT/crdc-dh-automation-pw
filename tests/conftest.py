"""Pytest fixtures shared by unit and live Hub tests.

`settings` and `locators` are session-scoped (load once).
`hub` is per test: one browser context, **already on Hub as that role**.
Tests write the scenario (navigate, assert). They do not call login_otp;
the fixture did. Use crdc_pw.auth.switch_user(hub, role) only when the case changes role.

storage_state: after Login.gov succeeds, cookies are written to
auth/<profile>/<Role>.json. The next run loads that file so we skip OTP if
the Hub session (connect.sid) is still valid. Files are gitignored.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from playwright.sync_api import Browser

from crdc_pw.auth import LoginSession
from crdc_pw.config import ROLES, Settings, load_settings
from crdc_pw.hub import Hub
from crdc_pw.locators.loader import LocatorLoader, repo_root

log = logging.getLogger("crdc_pw")

VIEWPORT = {"width": 1920, "height": 1080}


@pytest.fixture(scope="session")
def settings() -> Settings:
    return load_settings()


@pytest.fixture(scope="session")
def locators() -> LocatorLoader:
    return LocatorLoader()


def _storage_state_path(settings: Settings, role: str) -> Path:
    return repo_root() / "auth" / settings.profile / f"{role}.json"


@pytest.fixture
def hub(
    request: pytest.FixtureRequest,
    settings: Settings,
    locators: LocatorLoader,
) -> Hub:
    """Logged-in Hub session for one role.

    This is session setup (Katalon navigate + loginToCrdcOtp), not the test
    scenario. Parametrize with indirect=True so each role gets its own
    context — same idea as Katalon closing the browser between users.
    `browser` comes from pytest-playwright and is only requested after we know
    credentials exist, so unit tests never launch Chromium.
    """
    role = getattr(request, "param", "Admin")
    if role not in ROLES:
        raise KeyError(f"Unknown role '{role}'")
    creds = settings.role(role)
    if not creds.is_complete():
        pytest.skip(
            f"Missing {role}Email / {role}Password / {role}Secret in {settings.config_path.name}. "
            f"Copy config/{settings.profile}.yaml.example to config/{settings.profile}.yaml "
            "and fill the Katalon profile values."
        )
    browser: Browser = request.getfixturevalue("browser")
    path = _storage_state_path(settings, role)
    reuse = path.is_file()
    if reuse:
        log.info("Login %s: opening Hub with saved session %s", role, path.name)
    else:
        log.info("Login %s: no saved session, will use Login.gov OTP", role)
    context = browser.new_context(
        storage_state=str(path) if reuse else None,
        viewport=VIEWPORT,
    )
    context.set_default_timeout(15000)
    page = context.new_page()
    session = LoginSession(page, locators, settings)
    session.navigate()
    if session.is_logged_in(timeout_ms=3000):
        log.info("Login %s: Hub session is valid", role)
    else:
        log.info("Login %s: Login.gov OTP", role)
        session.login_otp(role)
        path.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(path))
        log.info("Login %s: saved session to %s", role, path.name)
    try:
        yield Hub(page=page, locators=locators, settings=settings, role=role)
    finally:
        context.close()
