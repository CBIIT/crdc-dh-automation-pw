"""Katalon WebUIUtils behaviors shared across Hub page objects (tooltips, button state)."""

from __future__ import annotations

import re
import time

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

__all__ = [
    "assert_button_enabled",
    "verify_tooltip_on_hover",
    "wait_for_button_stable",
]


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def verify_tooltip_on_hover(
    page: Page,
    trigger: Locator,
    expected_full: str,
    substring: str,
) -> None:
    """Hover trigger and assert a MUI tooltip matches expected_full (Katalon verifyTooltipOnHover)."""
    trigger.first.hover()
    page.wait_for_timeout(1000)
    tooltips = page.locator("[role='tooltip']")
    count = tooltips.count()
    match_text: str | None = None
    for i in range(count):
        text = tooltips.nth(i).inner_text()
        if substring in text:
            match_text = _normalize_whitespace(text)
            break
    if match_text is None:
        found = [tooltips.nth(i).inner_text() for i in range(count)]
        raise AssertionError(
            f"Tooltip with substring {substring!r} not found. Visible tooltips: {found!r}"
        )
    expected = _normalize_whitespace(expected_full)
    assert match_text == expected, (
        f"verify_tooltip_on_hover: expected {expected!r}, actual {match_text!r}"
    )


def wait_for_button_stable(
    button: Locator,
    *,
    enabled: bool,
    timeout_s: float = 30,
    poll_ms: int = 1000,
) -> None:
    """Poll until button.is_enabled() matches enabled (Katalon waitUntilStableForButtonEnabledOrDisabled)."""
    deadline = time.monotonic() + timeout_s
    label = "enabled" if enabled else "disabled"
    while time.monotonic() < deadline:
        try:
            if button.first.is_enabled() == enabled:
                return
        except Exception:
            pass
        button.page.wait_for_timeout(poll_ms)
    raise PlaywrightTimeoutError(
        f"wait_for_button_stable: timed out after {timeout_s}s waiting for {label} state"
    )


def assert_button_enabled(button: Locator, expected_enabled: bool) -> None:
    """Assert enabled/disabled (Katalon verifyButtonEnabled)."""
    if expected_enabled:
        expect(button.first).to_be_enabled()
    else:
        expect(button.first).to_be_disabled()
