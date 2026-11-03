"""Read Submission Request test data (Katalon Data Files section-a … section-d)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from crdc_pw.locators.loader import repo_root

INPUT_RELATIVE = Path("InputFiles/CRDC/SubmissionRequest/SubmissionRequest.xlsx")


def workbook_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / INPUT_RELATIVE


def get_sheet_row(sheet_name: str, data_row_num: int, root: Path | None = None) -> dict[str, Any]:
    """Return one data row as header → cell value (Katalon row 1 = first row after header)."""
    if data_row_num < 1:
        raise ValueError(f"data_row_num must be >= 1, got {data_row_num}")
    path = workbook_path(root)
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet_name]
        headers = [_cell_str(c.value) for c in next(ws.iter_rows(min_row=1, max_row=1))]
        excel_row = data_row_num + 1
        values = next(ws.iter_rows(min_row=excel_row, max_row=excel_row, values_only=True))
        row_dict: dict[str, Any] = {}
        for key, val in zip(headers, values):
            if key:
                row_dict[key] = val
        return row_dict
    finally:
        wb.close()


def _cell_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
