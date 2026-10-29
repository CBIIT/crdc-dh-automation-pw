"""Guards BasePage helpers that do not need a browser.

Flow:
  1. _trim turns None and blank into None
  2. _trim strips surrounding whitespace
  3. _trim leaves a non-blank string
"""

from __future__ import annotations

import pytest

from crdc_pw.pages.base import BasePage


pytestmark = pytest.mark.unit


def test_trim_none_stays_none() -> None:
    """Filter kwargs that were never passed must stay None, not empty string."""
    assert BasePage._trim(None) is None


def test_trim_blank_becomes_none() -> None:
    """Whitespace-only filter values are skipped the same as missing ones."""
    assert BasePage._trim("") is None
    assert BasePage._trim("   ") is None


def test_trim_strips_and_keeps_text() -> None:
    """A real filter value is stripped, not dropped."""
    assert BasePage._trim("  autoQA  ") == "autoQA"
