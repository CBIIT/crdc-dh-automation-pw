"""Read Submission Request test data (Katalon Data Files section-a … section-d)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from crdc_pw.locators.loader import repo_root

INPUT_RELATIVE = Path("InputFiles/CRDC/SubmissionRequest/SubmissionRequest.xlsx")


def workbook_path(root: Path | None = None) -> Path:
    """Absolute path to SubmissionRequest.xlsx under InputFiles/CRDC/SubmissionRequest."""
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


def find_cell_containing(
    sheet_name: str, column: str, token: str, root: Path | None = None
) -> str:
    """First non-empty cell in a column whose text contains token (case-insensitive).

    Used where Katalon mapped a short dropdown word (for example Cholangiocarcinoma or Homo)
    to the full list value on a fixed data row through a switch statement.
    """
    needle = token.strip().lower()
    if not needle:
        raise ValueError("token must not be empty")
    wb = load_workbook(workbook_path(root), read_only=True, data_only=True)
    try:
        ws = wb[sheet_name]
        rows = ws.iter_rows(values_only=True)
        headers = [_cell_str(v) for v in next(rows)]
        if column not in headers:
            raise KeyError(f"Column {column!r} not in sheet {sheet_name!r}")
        idx = headers.index(column)
        for values in rows:
            cell = _cell_str(values[idx]) if idx < len(values) else ""
            if cell and needle in cell.lower():
                return cell
    finally:
        wb.close()
    raise LookupError(f"No {column!r} cell containing {token!r} in sheet {sheet_name!r}")


def _cell_str(value: Any) -> str:
    """Header cell value as stripped string."""
    if value is None:
        return ""
    return str(value).strip()
