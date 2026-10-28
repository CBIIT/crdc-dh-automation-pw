"""Generate a Login.gov one-time code in-process.

Katalon shelled out to PythonFiles/CRDC/GenerateOtp.py. Same pyotp call, no subprocess.
"""

from __future__ import annotations

import pyotp


def totp_now(secret: str) -> str:
    """Return the current 6-digit TOTP for the account's secret."""
    if not secret or not str(secret).strip():
        raise ValueError("TOTP secret is empty")
    return pyotp.TOTP(str(secret).strip()).now()
