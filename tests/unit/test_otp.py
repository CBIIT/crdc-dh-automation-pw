"""TOTP helper uses a public RFC example secret, not a real Hub account.

Login.gov 2FA is the same TOTP Katalon generated in GenerateOtp.py.
These tests only check the helper shape — they do not talk to Login.gov.

Flow (this file):
  1. totp_now returns a six-digit code
  2. Blank secret is rejected (do not silently send an empty OTP)
"""

from __future__ import annotations

import re

import pytest

from crdc_pw.otp import totp_now

RFC_EXAMPLE_SECRET = "JBSWY3DPEHPK3PXP"


@pytest.mark.unit
def test_totp_now_is_six_digits() -> None:
    """A valid seed produces the six-digit string Login.gov expects."""
    code = totp_now(RFC_EXAMPLE_SECRET)
    assert re.fullmatch(r"\d{6}", code)


@pytest.mark.unit
def test_totp_now_rejects_empty_secret() -> None:
    """Missing *Secret in yaml should fail here, not as a Login.gov timeout."""
    with pytest.raises(ValueError, match="empty"):
        totp_now("  ")
