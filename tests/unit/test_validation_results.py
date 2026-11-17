"""No-browser checks for Validation Results expected-TSV matching (Katalon 1:1).

Does not open Hub.

Flow:
  1. Upload and expected filenames map to node names
  2. GC mappings sheet has diagnosis → study_diagnosis_id
  3. TC08 expected TSV loads Error / Invalid integer value rows
  4. Matching UI rows Pass; missing, extra, or wrong issue Fail
"""

from __future__ import annotations

import pytest

from crdc_pw.utils.validation_results import (
    diff_error_details_dialog_issues,
    diff_upload_errors,
    diff_validation_results,
    expected_upload_errors_dir,
    expected_error_detail_issues_for_row,
    find_expected_validation_results_tsv,
    list_nodes_from_expected_validation_results_folder,
    list_tsv_files_and_nodes_for_tc,
    load_all_expected_error_detail_rows_from_tsv,
    load_expected_upload_errors,
    load_expected_validation_results_tsv,
    load_validation_results_mappings,
    node_from_expected_validation_results_filename,
    node_from_filename,
    normalize_quotes,
    parse_expected_errors_cell,
    unquote_csv_style,
    unique_severity_issue_type_pairs_from_expected_tsv,
)

pytestmark = pytest.mark.unit


def test_node_from_upload_filename() -> None:
    """GC_diagnosis_v11.0.3.tsv is the diagnosis node."""
    assert node_from_filename("GC_diagnosis_v11.0.3.tsv") == "diagnosis"
    assert node_from_filename("GC_consent_group_v11.0.3.tsv") == "consent_group"


def test_node_from_expected_filename() -> None:
    """Expected VR filename strips suffix, version, and GC_ prefix."""
    name = "GC_diagnosis_v11.0.3_expected-ValidationResults.tsv"
    assert node_from_expected_validation_results_filename(name) == "diagnosis"
    assert node_from_expected_validation_results_filename("nope.tsv") == ""


def test_list_tc08_upload_tsvs_skips_expected_folder() -> None:
    """Only top-level TC08 TSVs are uploaded, not expected-ValidationResults."""
    files, nodes = list_tsv_files_and_nodes_for_tc("TC08")
    names = {path.name for path in files}
    assert "GC_diagnosis_v11.0.3.tsv" in names
    assert all("expected" not in path.as_posix() for path in files)
    assert "diagnosis" in nodes


def test_gc_mappings_include_diagnosis() -> None:
    """Sheet GC maps diagnosis to study_diagnosis_id."""
    mappings = load_validation_results_mappings("GC")
    assert mappings["diagnosis"] == "study_diagnosis_id"


def test_tc08_expected_rows_invalid_integer() -> None:
    """TC08 expected TSV has Error / Invalid integer value rows keyed by study_diagnosis_id."""
    nodes = list_nodes_from_expected_validation_results_folder("TC08")
    assert nodes == ["diagnosis"]
    path = find_expected_validation_results_tsv("TC08", "diagnosis")
    assert path is not None
    pairs = unique_severity_issue_type_pairs_from_expected_tsv(path)
    assert ("Error", "Invalid integer value") in pairs
    rows = load_expected_validation_results_tsv(
        path, "study_diagnosis_id", "Error", "Invalid integer value"
    )
    assert len(rows) >= 1
    submitted_id, issue, severity = rows[0]
    assert submitted_id
    assert issue == "Invalid integer value"
    assert severity == "Error"


def test_diff_matching_rows_pass() -> None:
    """UI rows that match expected submitted id, issue, and severity are Pass."""
    expected = [("id-1", "Invalid integer value", "Error")]
    actual = [("id-1", "Invalid integer value", "Error")]
    assert diff_validation_results(expected, actual, "Invalid integer value") == []


def test_diff_missing_id_fails() -> None:
    """Expected submitted id absent from the UI is a mismatch."""
    expected = [("id-1", "Invalid integer value", "Error")]
    errors = diff_validation_results(expected, [], "Invalid integer value")
    assert any("not found" in err for err in errors)


def test_diff_extra_id_fails() -> None:
    """UI submitted id not in the expected TSV is a mismatch."""
    expected = [("id-1", "Invalid integer value", "Error")]
    actual = [
        ("id-1", "Invalid integer value", "Error"),
        ("id-2", "Invalid integer value", "Error"),
    ]
    errors = diff_validation_results(expected, actual, "Invalid integer value")
    assert any("not in expected TSV" in err for err in errors)


def test_diff_issue_mismatch_fails() -> None:
    """Wrong Issue Type on a matching submitted id is a mismatch."""
    expected = [("id-1", "Invalid integer value", "Error")]
    actual = [("id-1", "Missing required property", "Error")]
    errors = diff_validation_results(expected, actual, "Invalid integer value")
    assert any("Issue Type" in err for err in errors)


def test_unquote_csv_style() -> None:
    """Excel-wrapped quotes become plain message text."""
    assert unquote_csv_style('"hello ""world"""') == 'hello "world"'


def test_tc04_error_detail_rows_from_study_expected_tsv() -> None:
    """TC04 study expected TSV supplies long Expected_Issues for error-details dialog."""
    path = find_expected_validation_results_tsv("TC04", "study")
    assert path is not None
    rows = load_all_expected_error_detail_rows_from_tsv(path, "study_id")
    assert len(rows) >= 1
    submitted_id, severity, issue_type, message = rows[0]
    assert submitted_id == "phs769076"
    assert severity == "Error"
    assert issue_type == "Missing required property"
    assert "study_description" in message
    issues = expected_error_detail_issues_for_row(severity, message)
    assert diff_error_details_dialog_issues(
        issues, [{"severity": "Error", "message": message}]
    ) == []


def test_error_detail_message_falls_back_to_issue_type() -> None:
    """When Expected_Issues is empty, dialog message equals Issue_Type."""
    path = find_expected_validation_results_tsv("TC08", "diagnosis")
    assert path is not None
    rows = load_all_expected_error_detail_rows_from_tsv(path, "study_diagnosis_id")
    assert rows
    _sid, _sev, issue_type, message = rows[0]
    assert message == issue_type


def test_diff_error_details_extra_actual_allowed() -> None:
    """Dialog may list more issues than expected; all expected must still match."""
    expected = [{"severity": "Error", "message": "Required property"}]
    actual = [
        {"severity": "Error", "message": "Required property study_description is empty."},
        {"severity": "Warning", "message": "Other issue"},
    ]
    assert diff_error_details_dialog_issues(expected, actual) == []


@pytest.mark.parametrize(
    "actual",
    [
        [],
        [{"severity": "Warning", "message": "Required property"}],
        [{"severity": "Error", "message": "Different issue"}],
    ],
)
def test_diff_error_details_missing_or_mismatched_issue_fails(
    actual: list[dict[str, str]],
) -> None:
    expected = [{"severity": "Error", "message": "Required property"}]
    assert diff_error_details_dialog_issues(expected, actual)


# --- Upload Errors modal oracle (887 TC101, 2864 TC102) ---


def test_parse_expected_errors_cell_plain_quoted_and_list() -> None:
    assert parse_expected_errors_cell("one message") == ["one message"]
    assert parse_expected_errors_cell('"say ""hi"" now"') == ['say "hi" now']
    assert parse_expected_errors_cell("['a', 'b']") == ["a", "b"]
    assert parse_expected_errors_cell("['a', \"b c\"]") == ["a", "b c"]
    assert parse_expected_errors_cell("['only']") == ["only"]


def test_parse_expected_errors_cell_blank_gives_nothing() -> None:
    assert parse_expected_errors_cell("") == []
    assert parse_expected_errors_cell("   ") == []
    assert parse_expected_errors_cell(None) == []
    assert parse_expected_errors_cell("[]") == []


def test_normalize_quotes_makes_curly_and_straight_equal() -> None:
    assert normalize_quotes("\u201cx\u201d and \u201ey\u201f") == '"x" and "y"'
    assert normalize_quotes(None) == ""


def test_diff_upload_errors_ignores_order_and_quote_style() -> None:
    expected = ['"a.tsv": "x" is required.', "second"]
    actual = ["second", "\u201ca.tsv\u201d: \u201cx\u201d is required."]
    assert diff_upload_errors(expected, actual) == ([], [])


def test_diff_upload_errors_reports_missing_and_extra() -> None:
    missing, extra = diff_upload_errors(["a", "b"], ["b", "c"])
    assert missing == ["a"]
    assert extra == ["c"]


def test_diff_upload_errors_counts_repeats() -> None:
    assert diff_upload_errors(["a", "a"], ["a"]) == (["a"], [])
    assert diff_upload_errors(["a"], ["a", "a"]) == ([], ["a"])


def test_expected_upload_errors_dir_is_not_the_validation_results_folder() -> None:
    folder = expected_upload_errors_dir("CRDCDH-887_TC101")
    assert folder.name == "expected"
    assert folder.parent.name == "CRDCDH-887_TC101"


@pytest.mark.parametrize(
    ("tc_name", "tsv_count", "error_count", "known_message"),
    [
        (
            "CRDCDH-887_TC101",
            5,
            5,
            '"GC_study_v10.0.0.tsv": "type" column is required.',
        ),
        (
            "CRDCDH-2864_TC102",
            4,
            4,
            '"GC_study_v10.0.0.tsv": Column "study_acronym" is required to generate composite ID.',
        ),
    ],
)
def test_upload_errors_inputs_match_what_the_tests_expect(
    tc_name: str, tsv_count: int, error_count: int, known_message: str
) -> None:
    """One expected error per uploaded TSV; the test asserts that many files in the batch row."""
    files, _nodes = list_tsv_files_and_nodes_for_tc(tc_name)
    assert len(files) == tsv_count
    errors = load_expected_upload_errors(tc_name)
    assert len(errors) == error_count
    assert known_message in errors


def test_load_expected_upload_errors_missing_folder_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_expected_upload_errors("no-such-tc")


def test_load_expected_upload_errors_without_any_errors_raises(tmp_path) -> None:
    folder = tmp_path / "InputFiles" / "CRDC" / "MetadataData" / "tc" / "expected"
    folder.mkdir(parents=True)
    (folder / "a_expected.tsv").write_text("type\texpected_errors\nx\t\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_expected_upload_errors("tc", root=tmp_path)


def test_load_expected_upload_errors_reads_column_case_insensitively(tmp_path) -> None:
    folder = tmp_path / "InputFiles" / "CRDC" / "MetadataData" / "tc" / "expected"
    folder.mkdir(parents=True)
    (folder / "a_expected.tsv").write_text(
        'type\t Expected_Errors \nx\t"msg ""q"""\ny\t\nz\t[\'m1\', \'m2\']\n', encoding="utf-8"
    )
    (folder / "b_no_column.tsv").write_text("type\tother\nx\tignored\n", encoding="utf-8")
    assert load_expected_upload_errors("tc", root=tmp_path) == ['msg "q"', "m1", "m2"]
