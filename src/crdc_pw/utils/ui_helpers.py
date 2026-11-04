"""Katalon WebUIUtils behaviors shared across Hub page objects (tooltips, button state)."""

from __future__ import annotations

import logging
import re
import time

from typing import Protocol

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

log = logging.getLogger("crdc_pw.ui_helpers")

__all__ = [
    "assert_button_enabled",
    "verify_tooltip_on_click",
    "verify_tooltip_on_click_page",
    "verify_tooltip_on_click_path",
    "verify_tooltip_on_hover",
    "verify_tooltip_on_hover_page",
    "wait_for_button_stable",
]

# Tooltip layering (Hub-backed tests should not pass raw Page):
# - verify_tooltip_on_click / verify_tooltip_on_hover — internal primitives (Page + Locator).
#   Prefer these inside page object methods that already hold self.page.
# - verify_tooltip_on_click_page / verify_tooltip_on_hover_page — test-facing when you have a
#   Hub-backed page object and a Locator (property or dynamic sibling), same tab as page_obj.
# - verify_tooltip_on_click_path — test-facing when the trigger is only a YAML locator path.


class _HubPageLike(Protocol):
    page: Page

    @property
    def locators(self): ...


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


def verify_tooltip_on_hover(page: Page, trigger: Locator, expected: str) -> None:
    """Internal primitive: hover trigger; assert a visible tooltip equals expected (whitespace-normalized).

    Picks among visible [role='tooltip'] nodes by full text match (no substring disambiguation).
    Tests should call verify_tooltip_on_hover_page instead.
    """
    trigger.first.hover()
    page.wait_for_timeout(1000)
    expected_norm = _normalize_whitespace(expected)
    tooltips = page.locator("[role='tooltip']")
    visible_texts: list[str] = []
    for i in range(tooltips.count()):
        tip = tooltips.nth(i)
        try:
            if not tip.is_visible():
                continue
        except Exception:
            continue
        actual_norm = _normalize_whitespace(tip.inner_text() or "")
        if actual_norm:
            visible_texts.append(actual_norm)
        if actual_norm == expected_norm:
            log.info(
                "Tooltip hover | expected: %s | actual: %s | Pass",
                expected_norm or "(empty)",
                actual_norm or "(empty)",
            )
            return
    if not visible_texts:
        actual_log = "(none visible)"
    elif len(visible_texts) == 1:
        actual_log = visible_texts[0] or "(empty)"
    else:
        actual_log = str(visible_texts)
    log.info(
        "Tooltip hover | expected: %s | actual: %s | Fail",
        expected_norm or "(empty)",
        actual_log,
    )
    raise AssertionError(
        f"verify_tooltip_on_hover: expected {expected_norm!r}, "
        f"visible tooltips: {visible_texts!r}"
    )


def verify_tooltip_on_hover_page(
    page_obj: _HubPageLike,
    trigger: Locator,
    expected: str,
) -> None:
    """Hub page object + Locator: hover tooltip assert (see module comment on layering)."""
    verify_tooltip_on_hover(page_obj.page, trigger, expected)


def verify_tooltip_on_click_page(
    page_obj: _HubPageLike,
    trigger: Locator,
    expected: str,
) -> None:
    """Hub page object + Locator: click tooltip assert (see module comment on layering)."""
    verify_tooltip_on_click(page_obj.page, trigger, expected)


def verify_tooltip_on_click_path(
    page_obj: _HubPageLike,
    yaml_path: str,
    expected: str,
) -> None:
    """Hub page object + YAML path: click tooltip assert (CRDCDH-3952 Section D info icons)."""
    verify_tooltip_on_click_page(
        page_obj,
        page_obj.page.locator(page_obj.locators.get(yaml_path)),
        expected,
    )


def verify_tooltip_on_click(page: Page, trigger: Locator, expected: str) -> None:
    """Internal primitive: click trigger, assert tooltip, dismiss (Katalon verifyTooltipOnClick).

    Tests should call verify_tooltip_on_click_page or verify_tooltip_on_click_path.
    """
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
