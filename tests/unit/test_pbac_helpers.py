"""No-browser checks for PBAC functional pass/fail polarity."""

from __future__ import annotations

import pytest

from crdc_pw.utils.pbac_helpers import _functional_scenario_passed


@pytest.mark.unit
@pytest.mark.parametrize(
    ("scenario", "result", "expected"),
    [
        ("positive", True, True),
        ("positive", False, False),
        ("negative", False, True),
        ("negative", True, False),
    ],
)
def test_functional_scenario_passed(scenario: str, result: bool, expected: bool) -> None:
    """Positive PASS when accessible; negative PASS when not accessible."""
    assert _functional_scenario_passed(scenario, result) is expected


@pytest.mark.unit
def test_functional_scenario_passed_rejects_unknown_scenario() -> None:
    with pytest.raises(ValueError, match="Unknown PBAC scenario"):
        _functional_scenario_passed("other", True)
