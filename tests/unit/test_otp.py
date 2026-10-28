"""TOTP helper uses a public RFC example secret, not a real Hub account."""

from __future__ import annotations

import re

import pytest

from crdc_pw.otp import totp_now

RFC_EXAMPLE_SECRET = "JBSWY3DPEHPK3PXP"


@pytest.mark.unit
def test_totp_now_is_six_digits() -> None:
    code = totp_now(RFC_EXAMPLE_SECRET)
    assert re.fullmatch(r"\d{6}", code)


@pytest.mark.unit
def test_totp_now_rejects_empty_secret() -> None:
    with pytest.raises(ValueError, match="empty"):
        totp_now("  ")
