"""Pure helpers for generic-table checks (sort order, pagination text). No browser.

BasePage reads the live table and hands the text here, so the compare rules can be unit tested.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# MUI writes "1-20 of 193" with an en dash; allow a plain hyphen too.
_DISPLAYED_ROWS = re.compile(r"(\d+)\s*[\u2013\-]\s*(\d+)\s+of\s+(\d+)")


class DisplayedRows(NamedTuple):
    """The three numbers in the pagination label "from-to of total"."""

    first: int
    last: int
    total: int


def parse_displayed_rows(text: str | None) -> DisplayedRows | None:
    """Parse the pagination label "1-20 of 193". Return None if it does not match."""
    match = _DISPLAYED_ROWS.search(text or "")
    if not match:
        return None
    return DisplayedRows(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def expected_page_count(total_rows: int, rows_per_page: int) -> int:
    """Pages needed for total_rows at rows_per_page each. An empty table still has one page."""
    if rows_per_page < 1:
        raise ValueError(f"rows_per_page must be at least 1, got {rows_per_page}")
    return max(1, -(-total_rows // rows_per_page))


def _compare(a: str, b: str) -> int:
    """Negative, zero or positive like Java compare: numbers first, then case-insensitive text."""
    try:
        x, y = float(a), float(b)
    except ValueError:
        x, y = a.lower(), b.lower()  # type: ignore[assignment]
    return (x > y) - (x < y)  # type: ignore[operator]


def is_sorted(values: list[str], direction: str) -> bool:
    """True when each neighbouring pair is in order for direction asc or desc.

    A pair is compared as numbers when both parse, otherwise as case-insensitive text. A pair
    with a blank value is skipped, so a missing cell never fails the order check. Fewer than
    two values is sorted.
    """
    want = direction.strip().lower()
    if want not in ("asc", "desc"):
        raise ValueError(f"direction must be asc or desc, got {direction!r}")
    for left, right in zip(values, values[1:]):
        a, b = (left or "").strip(), (right or "").strip()
        if not a or not b:
            continue
        order = _compare(a, b)
        if want == "asc" and order > 0:
            return False
        if want == "desc" and order < 0:
            return False
    return True
