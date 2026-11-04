"""Guards automation DS display names for parallel-safe create (no Hub)."""

from __future__ import annotations

import re

import pytest

from crdc_pw.pages.data_submissions import (
    AUTOMATION_SUBMISSION_NAME_LEN,
    _automation_submission_name,
)

pytestmark = pytest.mark.unit

_NAME_PATTERN = re.compile(r"^auto-test_\d{8}_\d{2}[0-9a-f]{4}$")


def test_automation_submission_name_format() -> None:
    """Name is 25 chars: date, hour digits, and four hex in the time segment."""
    name = _automation_submission_name()
    assert len(name) == AUTOMATION_SUBMISSION_NAME_LEN
    assert name.startswith("auto-test_")
    assert _NAME_PATTERN.match(name)


def test_automation_submission_name_unique() -> None:
    """Two calls should not collide (parallel workers on shared Submitter)."""
    assert _automation_submission_name() != _automation_submission_name()
