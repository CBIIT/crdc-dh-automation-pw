"""No-browser checks for the Data Explorer expected-TSV oracle (Katalon DataExplorer keywords).

Does not open Hub.

Flow:
  1. Expected TSV for a node loads without type and dotted columns, sorted by the first column
  2. UI headers map to expected headers (case and underscore insensitive)
  3. The diff checks row count, missing headers and each cell (equal or contained)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crdc_pw.utils.data_explorer_results import (
    diff_data_explorer_table,
    find_expected_data_explorer_tsv,
    load_expected_data_explorer_table,
    map_expected_headers_to_ui,
)

pytestmark = pytest.mark.unit


def _write_tsv(root: Path, tc: str, name: str, text: str, sub: str = "") -> None:
    folder = root / "InputFiles" / "CRDC" / "MetadataData" / tc / sub
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text, encoding="utf-8")


def test_load_expected_participant_table_from_seed_folder() -> None:
    """CRDCDH-3026 participant.tsv: type and dotted columns dropped, rows sorted by id."""
    headers, rows = load_expected_data_explorer_table("CRDCDH-3026", "participant")
    assert headers == ["study_participant_id", "participant_id", "race", "sex", "ethnicity", "dbGaP_subject_id"]
    assert [row[0] for row in rows] == ["partsof1", "partsof2", "partsof3", "partsof4", "partsof5"]
    assert rows[0][2] == "Asian|American Indian or Alaska Native"


def test_load_expected_program_table_from_seed_folder() -> None:
    headers, rows = load_expected_data_explorer_table("CRDCDH-3026", "program")
    assert headers[:3] == ["program_name", "program_acronym", "program_short_description"]
    assert rows == [["auto_program", "AUTOPROGRAM", "pgm short", "full desc", "https://program1", "short name", "NCI"]]


def test_load_expected_unknown_node_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_expected_data_explorer_table("CRDCDH-3026", "no_such_node")


def test_find_expected_tsv_uses_metadata_subfolder_and_ignores_case(tmp_path: Path) -> None:
    _write_tsv(tmp_path, "TC", "GC_Sample_v1.0.0.tsv", "type\tsample_id\nsample\ts1\n", sub="Metadata")
    path = find_expected_data_explorer_tsv("TC", "sample", root=tmp_path)
    assert path is not None and path.name == "GC_Sample_v1.0.0.tsv"
    assert find_expected_data_explorer_tsv("TC", "study", root=tmp_path) is None


def test_find_expected_tsv_matches_plain_name_with_underscore() -> None:
    """consent_group.tsv is consent_group, though node_from_filename reads it as group."""
    path = find_expected_data_explorer_tsv("CRDCDH-3026", "consent_group")
    assert path is not None and path.name == "consent_group.tsv"


def test_find_expected_tsv_literal_name_wins_over_upload_style_name(tmp_path: Path) -> None:
    _write_tsv(tmp_path, "TC", "GC_study_arm.tsv", "type\tid\nstudy_arm\tupload\n")
    _write_tsv(tmp_path, "TC", "study_arm.tsv", "type\tid\nstudy_arm\tliteral\n")
    path = find_expected_data_explorer_tsv("TC", "study_arm", root=tmp_path)
    assert path is not None and path.name == "study_arm.tsv"
    # The upload-style name is still found when there is no plain file
    (tmp_path / "InputFiles" / "CRDC" / "MetadataData" / "TC" / "study_arm.tsv").unlink()
    path = find_expected_data_explorer_tsv("TC", "study_arm", root=tmp_path)
    assert path is not None and path.name == "GC_study_arm.tsv"


def test_load_unquotes_values_and_sorts_ignoring_case(tmp_path: Path) -> None:
    _write_tsv(tmp_path, "TC", "study.tsv", 'type\tstudy_id\tnote\nstudy\tb2\t"quoted"\nstudy\tA1\t\n')
    headers, rows = load_expected_data_explorer_table("TC", "study", root=tmp_path)
    assert headers == ["study_id", "note"]
    assert rows == [["A1", ""], ["b2", "quoted"]]


def test_map_expected_headers_ignores_case_and_underscore() -> None:
    mapping = map_expected_headers_to_ui(["study_id", "dbGaP_subject_id", "gone"], ["Study Id", "dbgap subject id"])
    assert mapping == [0, 1, -1]


_HEADERS = ["sample_id", "sample_type"]
_ROWS = [["auto_sample1", "Cells"], ["auto_sample2", "Tissue"]]


def test_diff_matches_when_headers_are_displayed_names() -> None:
    assert diff_data_explorer_table(_HEADERS, _ROWS, ["Sample Id", "Sample Type"], _ROWS) == []


def test_diff_row_count_mismatch_skips_cell_compare() -> None:
    problems = diff_data_explorer_table(_HEADERS, _ROWS, _HEADERS, _ROWS[:1])
    assert problems == ["Row count expected 2, actual 1"]


def test_diff_missing_column_is_reported() -> None:
    problems = diff_data_explorer_table(_HEADERS, _ROWS, ["sample_id"], [[r[0]] for r in _ROWS])
    assert any("'sample_type' is missing" in p for p in problems)


def test_diff_cell_mismatch_names_row_and_column() -> None:
    actual = [["auto_sample1", "Cells"], ["auto_sample2", "Bone Marrow"]]
    problems = diff_data_explorer_table(_HEADERS, _ROWS, _HEADERS, actual)
    assert problems == ["Row 2 column 'sample_type': expected 'Tissue', actual 'Bone Marrow'"]


def test_diff_truncated_expected_matches_contained_text() -> None:
    expected = [["a", "A long description..."]]
    actual = [["a", "A long description that the table shows in full"]]
    assert diff_data_explorer_table(["id", "text"], expected, ["id", "text"], actual) == []


def test_diff_blank_expected_requires_blank_ui_value() -> None:
    expected = [["a", ""]]
    problems = diff_data_explorer_table(["id", "acc"], expected, ["id", "acc"], [["a", "PRJNA123"]])
    assert problems == ["Row 1 column 'acc': expected '', actual 'PRJNA123'"]


def test_diff_blank_expected_matches_blank_ui_value() -> None:
    assert diff_data_explorer_table(["id", "acc"], [["a", ""]], ["id", "acc"], [["a", ""]]) == []
