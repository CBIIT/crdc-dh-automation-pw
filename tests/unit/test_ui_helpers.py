"""No-browser checks for the ui_helpers pure helpers (Full History status comparison, Katalon verifyFullSubmissionHistory)."""

from __future__ import annotations

from crdc_pw.utils.ui_helpers import diff_history_statuses, normalize_history_status

EXPECTED = ["COMPLETED", "RELEASED", "SUBMITTED", "REJECTED", "SUBMITTED", "INPROGRESS", "NEW"]


def test_normalize_strips_whitespace_and_uppercases() -> None:
    assert normalize_history_status("In Progress") == "INPROGRESS"
    assert normalize_history_status("  new \n") == "NEW"
    assert normalize_history_status("") == ""


def test_matching_history_is_none_even_with_spacing_and_case() -> None:
    actual = ["Completed", "Released", "Submitted", "Rejected", "Submitted", "In Progress", "New"]
    assert diff_history_statuses(EXPECTED, actual) is None


def test_order_mismatch_is_reported() -> None:
    actual = list(reversed(EXPECTED))
    reason = diff_history_statuses(EXPECTED, actual)
    assert reason is not None
    assert "expected COMPLETED" in reason


def test_missing_and_extra_rows_are_reported() -> None:
    assert diff_history_statuses(EXPECTED, EXPECTED[:-1]) is not None
    assert diff_history_statuses(EXPECTED, [*EXPECTED, "NEW"]) is not None
