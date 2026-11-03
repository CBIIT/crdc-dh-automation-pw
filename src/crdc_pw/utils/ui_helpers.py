"""Katalon WebUIUtils behaviors shared across Hub page objects (tooltips, button state)."""

from __future__ import annotations

import logging
import re
import time

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

log = logging.getLogger("crdc_pw.ui_helpers")

__all__ = [
    "assert_button_enabled",
    "verify_tooltip_on_click",
    "verify_tooltip_on_hover",
    "wait_for_button_stable",
]


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _dismiss_click_tooltip(page: Page, trigger: Locator) -> None:
    """Close a click-toggle MUI tooltip so the next trigger is not covered."""
    tooltips = page.locator("[role='tooltip']")
    if tooltips.count() == 0:
        return
    try:
        if not tooltips.first.is_visible():
            return
    except Exception:
        return
    page.keyboard.press("Escape")
    try:
        tooltips.first.wait_for(state="hidden", timeout=2000)
        return
    except PlaywrightTimeoutError:
        pass
    trigger.first.click(force=True)
    try:
        tooltips.first.wait_for(state="hidden", timeout=2000)
    except PlaywrightTimeoutError:
        log.warning("Tooltip still visible after dismiss attempt")


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


def verify_tooltip_on_click(page: Page, trigger: Locator, expected: str) -> None:
    """Click trigger and assert a MUI tooltip equals expected (full string, whitespace-normalized)."""
    expected_norm = _normalize_whitespace(expected)
    trigger.first.click()
    tooltips = page.locator("[role='tooltip']")
    try:
        tooltips.first.wait_for(state="visible", timeout=5000)
    except PlaywrightTimeoutError:
        log.info("Tooltip expected: %s", expected_norm)
        log.info("Tooltip actual: (no visible tooltip after click)")
        raise AssertionError(
            f"verify_tooltip_on_click: no visible tooltip; expected {expected_norm!r}"
        ) from None

    count = tooltips.count()
    actual_norm: str | None = None
    all_normalized: list[str] = []
    for i in range(count):
        text = tooltips.nth(i).inner_text()
        if not tooltips.nth(i).is_visible():
            continue
        norm = _normalize_whitespace(text)
        all_normalized.append(norm)
        if norm == expected_norm:
            actual_norm = norm
            break

    if actual_norm is None:
        actual_norm = all_normalized[0] if all_normalized else "(empty)"
        log.info("Tooltip expected: %s", expected_norm)
        log.info("Tooltip actual: %s", actual_norm)
        if len(all_normalized) > 1:
            log.info("Tooltip all visible: %s", all_normalized)
        raise AssertionError(
            f"verify_tooltip_on_click: expected {expected_norm!r}, actual {actual_norm!r}"
        )

    log.info("Tooltip expected: %s", expected_norm)
    log.info("Tooltip actual: %s", actual_norm)
    assert actual_norm == expected_norm, (
        f"verify_tooltip_on_click: expected {expected_norm!r}, actual {actual_norm!r}"
    )
    _dismiss_click_tooltip(page, trigger)


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
