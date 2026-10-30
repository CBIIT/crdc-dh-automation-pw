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
    diff_validation_results,
    find_expected_validation_results_tsv,
    list_nodes_from_expected_validation_results_folder,
    list_tsv_files_and_nodes_for_tc,
    load_expected_validation_results_tsv,
    load_validation_results_mappings,
    node_from_expected_validation_results_filename,
    node_from_filename,
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
