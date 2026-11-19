"""No-browser checks for the upload CLI final-manifest oracles (CRDCDH-1405 TC101).

Flow (this file):
  1. final_manifest_path and read_manifest
  2. diff_final_manifest: valid, missing column, bad ids, row count, no rows
  3. diff_file_ids_between_runs: same, changed, missing and extra files
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crdc_pw.utils.cli_manifest import (
    diff_file_ids_between_runs,
    diff_final_manifest,
    final_manifest_path,
    is_valid_file_id,
    read_manifest,
)

pytestmark = pytest.mark.unit

_ID_A = "dg.4DFC/5bdb2b5c-984d-5562-b329-1631f206c7da"
_ID_B = "dg.4DFC/19aaa25d-4e69-56e2-bd4c-acc26d8bf825"
_ORIGINAL = (["type", "file_name"], [["file", "a.txt"], ["file", "b.csv"]])


def _final(rows: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    return ["type", "file_name", "internal_file_name", "file_id"], rows


def test_final_manifest_path_replaces_tsv_suffix() -> None:
    assert final_manifest_path(Path("/x/DataFiles/manifest.tsv")) == Path("/x/DataFiles/manifest-final.tsv")


def test_read_manifest_skips_blank_lines_and_trims(tmp_path: Path) -> None:
    path = tmp_path / "manifest.tsv"
    path.write_text("type\tfile_name\n\nfile\t a.txt \n", encoding="utf-8")
    assert read_manifest(path) == (["type", "file_name"], [["file", "a.txt"]])


def test_read_manifest_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "manifest.tsv"
    path.write_text("", encoding="utf-8")
    assert read_manifest(path) == ([], [])


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        (_ID_A, True),
        ("5bdb2b5c-984d-5562-b329-1631f206c7da", True),
        ("dg.4DFC/not-a-uuid", False),
        ("DG.4DFC/5bdb2b5c-984d-5562-b329-1631f206c7da", False),
        ("", False),
    ],
)
def test_is_valid_file_id(value: str, valid: bool) -> None:
    assert is_valid_file_id(value) is valid


def test_diff_final_manifest_valid() -> None:
    final = _final([["file", "a.txt", "a.txt", _ID_A], ["file", "b.csv", "b.csv", _ID_B]])
    assert diff_final_manifest(_ORIGINAL, final) == []


def test_diff_final_manifest_without_rows() -> None:
    assert diff_final_manifest(_ORIGINAL, _final([])) == ["Final manifest has no data rows"]


def test_diff_final_manifest_row_count_mismatch() -> None:
    final = _final([["file", "a.txt", "a.txt", _ID_A]])
    assert diff_final_manifest(_ORIGINAL, final) == ["Row count expected 2, actual 1"]


def test_diff_final_manifest_missing_file_id_column() -> None:
    final = (["type", "file_name"], [["file", "a.txt"], ["file", "b.csv"]])
    assert diff_final_manifest(_ORIGINAL, final) == ["Final manifest has no 'file_id' column"]


def test_diff_final_manifest_reports_empty_and_invalid_ids() -> None:
    final = _final([["file", "a.txt", "a.txt", ""], ["file", "b.csv", "b.csv", "dg.4DFC/nope"]])
    assert diff_final_manifest(_ORIGINAL, final) == [
        "Row 1: empty file_id",
        "Row 2: invalid file_id 'dg.4DFC/nope'",
    ]


def test_diff_file_ids_between_runs_same() -> None:
    rows = [["file", "a.txt", "a.txt", _ID_A], ["file", "b.csv", "b.csv", _ID_B]]
    assert diff_file_ids_between_runs(_final(rows), _final(list(reversed(rows)))) == []


def test_diff_file_ids_between_runs_changed_missing_and_extra() -> None:
    first = _final([["file", "a.txt", "a.txt", _ID_A], ["file", "b.csv", "b.csv", _ID_B]])
    second = _final([["file", "a.txt", "a.txt", _ID_B], ["file", "c.tsv", "c.tsv", _ID_A]])
    assert diff_file_ids_between_runs(first, second) == [
        f"a.txt: first={_ID_A}, second={_ID_B}",
        "b.csv: missing in second manifest",
        "c.tsv: missing in first manifest (extra in second)",
    ]


def test_diff_file_ids_between_runs_needs_both_columns() -> None:
    with pytest.raises(ValueError):
        diff_file_ids_between_runs((["file_name"], [["a.txt"]]), _final([]))
