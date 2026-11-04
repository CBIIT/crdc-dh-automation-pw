"""Pytest fixtures shared by unit and live Hub tests.

`settings` and `locators` are session-scoped (load once).
`hub` is per test: one browser context, **already on Hub as that role**.
Tests write the scenario (navigate, assert). They do not call login_otp;
the fixture did. Use crdc_pw.auth.switch_user(hub, role) only when the case changes role.

OTP is file-locked once per role (`ensure_storage_state`). Each test loads
auth/<profile>/<Role>.json into a new context and lands on Hub. Files are gitignored.
"""

from __future__ import annotations

import base64
import logging
import re
from datetime import datetime

import pytest
from playwright.sync_api import Browser
from playwright.sync_api import Page
from playwright.sync_api import expect
from pytest_html import extras as html_extras

from crdc_pw.auth import open_signed_in_page
from crdc_pw.config import ROLES, Settings, load_settings
from crdc_pw.hub import Hub
from crdc_pw.locators.loader import LocatorLoader, repo_root
from crdc_pw.pages.base import BasePage

log = logging.getLogger("crdc_pw")

pytest_plugins = ["crdc_pw.utils.excel_ds_test_runner.test_collector"]

_FAILURE_PNG = pytest.StashKey[bytes]()


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Katalon-style: a new HTML report per run unless --html is already set.

    Writes reports/report-YYYYMMDD-HHMMSS.html (gitignored). tryfirst so
    pytest-html sees the path when it registers.
    """
    expect.set_options(timeout=BasePage.DEFAULT_MS)
    if getattr(config.option, "htmlpath", None):
        return
    reports = repo_root() / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = reports / f"report-{stamp}.html"
    config.option.htmlpath = str(path)
    config.option.self_contained_html = True
    log.info("HTML report: %s", path)


def _failure_screenshot(page: Page | None) -> bytes | None:
    """Full-page PNG of the Hub tab, or None if the page is already gone."""
    if page is None:
        return None
    try:
        if page.is_closed():
            return None
        return page.screenshot(full_page=True, type="png")
    except Exception as exc:
        log.info("Could not take failure screenshot: %s", exc)
        return None


def _attach_failure_screenshot(item: pytest.Item, report: pytest.TestReport, png: bytes) -> None:
    """Embed the PNG in the HTML report and write a copy under reports/screenshots/."""
    extras = list(getattr(report, "extras", []) or [])
    extras.append(html_extras.png(base64.b64encode(png).decode("ascii"), name="Failure screenshot"))
    report.extras = extras
    safe = re.sub(r"[^\w.-]+", "_", f"{item.nodeid}-{report.when}")[:180]
    shot_dir = repo_root() / "reports" / "screenshots"
    shot_dir.mkdir(parents=True, exist_ok=True)
    path = shot_dir / f"{safe}.png"
    path.write_bytes(png)
    log.info("Failure screenshot: %s", path)


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """On setup/call failure, attach a Hub screenshot to the HTML report (Katalon-style)."""
    outcome = yield
    report = outcome.get_result()
    if not report.failed or report.when not in ("setup", "call"):
        return
    png = item.stash.get(_FAILURE_PNG, None)
    if png is None and report.when == "call":
        hub = item.funcargs.get("hub")
        png = _failure_screenshot(getattr(hub, "page", None))
    if png:
        _attach_failure_screenshot(item, report, png)


@pytest.fixture(scope="session")
def settings() -> Settings:
    return load_settings()


@pytest.fixture(scope="session")
def locators() -> LocatorLoader:
    return LocatorLoader()


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
    `browser` and `new_context` come from pytest-playwright and are only
    requested after we know credentials exist, so unit tests never launch
    Chromium. `new_context` is what records --tracing=retain-on-failure.
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
    create_context = request.getfixturevalue("new_context")
    page: Page | None = None
    live: Hub | None = None

    def remember_page(opened: Page) -> None:
        nonlocal page
        page = opened

    try:
        page = open_signed_in_page(
            browser,
            locators,
            settings,
            role,
            create_context=create_context,
            on_page=remember_page,
        )
        live = Hub(
            page=page,
            locators=locators,
            settings=settings,
            role=role,
            create_context=create_context,
        )
        yield live
    except Exception:
        png = _failure_screenshot(live.page if live is not None else page)
        if png:
            request.node.stash[_FAILURE_PNG] = png
        raise
    finally:
        closing = live.page if live is not None else page
        if closing is not None and not closing.is_closed():
            closing.context.close()
