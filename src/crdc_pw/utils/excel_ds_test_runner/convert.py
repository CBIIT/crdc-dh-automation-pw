"""Convert a TC*.xlsx case workbook to the TSV case format.

Usage:
    python -m crdc_pw.utils.excel_ds_test_runner.convert PATH.xlsx [PATH2.xlsx ...]
    python -m crdc_pw.utils.excel_ds_test_runner.convert --all [--out-dir DIR]

By default each TSV is written next to its workbook. Workbooks are never modified or
deleted. A case stem must not exist in both formats at once, so move or delete the
workbook once you switch a case to TSV (the collector fails on duplicates).
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

from crdc_pw.locators.loader import repo_root
from crdc_pw.utils.excel_ds_test_runner.loader import (
    SETTINGS_SHEET,
    STEPS_SHEET,
    _cell_str,
    _read_workbook_rows,
)


def _tsv_line(cells: list[str]) -> str:
    buf = io.StringIO()
    csv.writer(buf, delimiter="\t", lineterminator="\n").writerow(cells)
    return buf.getvalue()


def workbook_to_tsv(path: Path) -> str:
    """Return the TSV text equivalent to the Settings and Steps sheets of a workbook."""
    out: list[str] = []
    for row in _read_workbook_rows(path, SETTINGS_SHEET):
        if not row or row[0] is None:
            continue
        key = _cell_str(row[0])
        if not key or key.lower() == "key":
            continue
        value = _cell_str(row[1]) if len(row) > 1 else ""
        out.append(_tsv_line([f"# {key}", value]))

    steps = _read_workbook_rows(path, STEPS_SHEET)
    last = max((i for i, row in enumerate(steps) if any(_cell_str(c) for c in row)), default=-1)
    for row in steps[: last + 1]:
        cells = [_cell_str(c) for c in row[:4]]
        cells += [""] * (4 - len(cells))
        out.append(_tsv_line(cells))
    return "".join(out)


def convert_workbook(path: Path, out_dir: Path | None = None) -> Path:
    """Write the TSV for a workbook and return the TSV path."""
    target_dir = out_dir if out_dir is not None else path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{path.stem}.tsv"
    target.write_text(workbook_to_tsv(path), encoding="utf-8", newline="")
    return target


def _all_workbooks() -> list[Path]:
    return sorted(
        p
        for p in repo_root().glob("tests/DataValidation/**/TC*.xlsx")
        if not p.name.startswith(("~$", "TC_Template"))
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("workbooks", nargs="*", type=Path, help="TC*.xlsx files to convert")
    parser.add_argument("--all", action="store_true", help="convert every committed workbook")
    parser.add_argument("--out-dir", type=Path, help="write TSVs here instead of next to the workbook")
    args = parser.parse_args(argv)

    paths = _all_workbooks() if args.all else list(args.workbooks)
    if not paths:
        parser.error("give one or more workbooks, or --all")
    for path in paths:
        print(convert_workbook(path, args.out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
