#!/usr/bin/env python3
"""Run Excel Data Validation cases (tests/DataValidation/**/*.xlsx).

Examples (from repo root, venv active):
  python scripts/run_excel_ds_validation.py
  python scripts/run_excel_ds_validation.py TC09
  python scripts/run_excel_ds_validation.py TC08 --headed
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Excel Data Validation Hub tests (one .xlsx workbook per case)."
    )
    parser.add_argument(
        "case",
        nargs="?",
        help="Match one case by id or name fragment (e.g. TC09, VerifyInvalidInteger). Omit to run all enabled workbooks.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window (pytest --headed).",
    )
    args = parser.parse_args(argv)

    cmd: list[str] = [
        sys.executable,
        "-m",
        "pytest",
        "tests/DataValidation",
        "-m",
        "CRDC_DataValidation_Excel",
    ]
    if args.case:
        cmd.extend(["-k", args.case])
    if args.headed:
        cmd.append("--headed")

    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
