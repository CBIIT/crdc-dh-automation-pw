"""Guards the Hub wait policy numbers on BasePage (no browser).

Flow:
  1. DEFAULT_MS is 15s (context + expect)
  2. PROBE_MS is shorter than DEFAULT_MS
  3. Release Notes may wait longer than DEFAULT_MS
"""

from __future__ import annotations

import pytest

from crdc_pw.pages.base import BasePage


pytestmark = pytest.mark.unit


def test_default_is_fifteen_seconds() -> None:
    """Hub actions and expect() share 15s; do not drift back to Playwright's 5s expect default."""
    assert BasePage.DEFAULT_MS == 15_000


def test_probe_is_shorter_than_default() -> None:
    """Optional chrome must not sit on the full Hub timeout when the control is absent."""
    assert 0 < BasePage.PROBE_MS < BasePage.DEFAULT_MS


def test_release_notes_may_exceed_default() -> None:
    """GitHub markdown fetch on /release-notes is allowed more than the Hub default."""
    assert BasePage.RELEASE_NOTES_MS >= BasePage.DEFAULT_MS
