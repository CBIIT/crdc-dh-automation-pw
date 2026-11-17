"""No-browser guards for the generic-table sort and pagination checks (TC03, TC04)."""

from __future__ import annotations

import pytest

from crdc_pw.locators.loader import LocatorLoader
from crdc_pw.pages import base
from crdc_pw.utils.table_helpers import (
    DisplayedRows,
    expected_page_count,
    is_sorted,
    parse_displayed_rows,
)

pytestmark = pytest.mark.unit


# --- is_sorted ---


def test_is_sorted_text_ignores_case() -> None:
    assert is_sorted(["apple", "Banana", "cherry"], "asc")
    assert not is_sorted(["apple", "Banana", "cherry"], "desc")
    assert is_sorted(["Zed", "mid", "Alpha"], "desc")
    assert not is_sorted(["b", "a"], "asc")


def test_is_sorted_numbers_compare_as_numbers() -> None:
    """9 comes before 10 as a number, but after it as text."""
    assert is_sorted(["9", "10", "100"], "asc")
    assert is_sorted(["100", "10", "9"], "desc")
    assert not is_sorted(["10", "9"], "asc")


def test_is_sorted_equal_values_are_sorted_both_ways() -> None:
    assert is_sorted(["a", "a", "a"], "asc")
    assert is_sorted(["a", "a", "a"], "desc")


def test_is_sorted_skips_pairs_with_a_blank() -> None:
    assert is_sorted(["a", "", "b"], "asc")
    assert is_sorted(["b", "  ", "a"], "desc")
    # Only neighbouring pairs are compared, so a blank hides the pair on each side of it.
    assert is_sorted(["b", "", "a"], "asc")
    assert not is_sorted(["b", "a", "", "c"], "asc")


def test_is_sorted_short_lists_are_sorted() -> None:
    assert is_sorted([], "asc")
    assert is_sorted(["x"], "desc")


def test_is_sorted_direction_is_case_insensitive_and_checked() -> None:
    assert is_sorted(["a", "b"], "ASC")
    with pytest.raises(ValueError):
        is_sorted(["a", "b"], "up")


# --- parse_displayed_rows ---


def test_parse_displayed_rows_en_dash_and_hyphen() -> None:
    assert parse_displayed_rows("1\u201320 of 193") == DisplayedRows(1, 20, 193)
    assert parse_displayed_rows("21-40 of 193") == DisplayedRows(21, 40, 193)
    assert parse_displayed_rows("  181 \u2013 193 of 193 ") == DisplayedRows(181, 193, 193)
    assert parse_displayed_rows("0-0 of 0") == DisplayedRows(0, 0, 0)


def test_parse_displayed_rows_rejects_other_text() -> None:
    assert parse_displayed_rows("") is None
    assert parse_displayed_rows(None) is None
    assert parse_displayed_rows("Showing everything") is None
    assert parse_displayed_rows("1 of 5") is None


# --- expected_page_count ---


def test_expected_page_count_rounds_up() -> None:
    assert expected_page_count(193, 20) == 10
    assert expected_page_count(200, 20) == 10
    assert expected_page_count(201, 20) == 11
    assert expected_page_count(193, 5) == 39
    assert expected_page_count(20, 20) == 1


def test_expected_page_count_empty_table_has_one_page() -> None:
    assert expected_page_count(0, 20) == 1


def test_expected_page_count_rejects_bad_page_size() -> None:
    with pytest.raises(ValueError):
        expected_page_count(10, 0)


# --- locator keys the BasePage table methods use ---

_TABLE_KEYS = [
    base._GENERIC_TABLE_ROW,
    base._GENERIC_TABLE_HEADER,
    base._GENERIC_TABLE_LOADING_ROW,
    base._ROWS_PER_PAGE,
    base._DISPLAYED_ROWS,
    base._NEXT_PAGE,
    base._PREVIOUS_PAGE,
    base._CURRENT_PAGE,
    base._GO_TO_PAGE,
    base._PAGE_BUTTONS,
]


def test_table_locator_keys_exist(locators: LocatorLoader) -> None:
    missing = [path for path in _TABLE_KEYS if not locators.has(path)]
    assert missing == [], f"generic table locators not in YAML: {missing}"


def test_go_to_page_button_fills_the_page_number(locators: LocatorLoader) -> None:
    assert "Go to page 7'" in locators.get(base._GO_TO_PAGE, page="7")
