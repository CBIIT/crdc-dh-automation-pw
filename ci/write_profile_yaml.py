"""CLI for GitHub Actions: materialize the gitignored profile yaml from secrets.

    python ci/write_profile_yaml.py

Reads CRDC_PROFILE (default qa) and Katalon-named env vars set from
${{ secrets.AdminEmail }} etc. See ci/README.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crdc_pw.config import write_profile_yaml  # noqa: E402


def main() -> None:
    write_profile_yaml(ROOT)


if __name__ == "__main__":
    main()
