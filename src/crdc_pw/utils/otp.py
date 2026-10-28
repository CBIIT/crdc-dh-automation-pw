"""Generate a Login.gov one-time code in-process.

Katalon shelled out to PythonFiles/CRDC/GenerateOtp.py. Same pyotp call, no subprocess.
"""

from __future__ import annotations

import pyotp


def totp_now(secret: str) -> str:
    """Return the current 6-digit Login.gov TOTP for this account's secret.

    Same call as Katalon PythonFiles/CRDC/GenerateOtp.py, in-process (no
    subprocess). Empty secret fails here instead of sending a blank OTP.
    """
    if not secret or not str(secret).strip():
        raise ValueError("TOTP secret is empty")
    return pyotp.TOTP(str(secret).strip()).now()
