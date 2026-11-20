"""No-browser tests for the CLI run checks in cli_verifications (CRDCDH-1405 TC101, CRDCDH-697 TC13).

Flow (this file):
  Final manifest (Katalon verifyFinalManifest and verifyFinalManifestDeterministic)
    1. final_manifest_path and read_manifest
    2. diff_final_manifest: valid, missing column, bad ids, row count, no rows
    3. diff_file_ids_between_runs: same, changed, missing and extra files
       verify_final_manifest and verify_final_manifest_deterministic: the keywords the test calls
  CLI error messages (Katalon verifyCliErrorMessages)
    4. normalize_error_cell and find_column
    5. load_expected_errors_by_file_name (expected/*.tsv)
    6. latest_upload_report and read_upload_report (the CLI's tmp/upload-report-*.tsv)
    7. Log helpers (strip_log_prefix, extract_error_from_log, find_cli_log) fill in empty report cells
    8. compare_cli_errors and verify_cli_error_messages compare and write the report
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from crdc_pw.pages.cli_uploader import CliResult, CliUpload
from crdc_pw.utils.cli_verifications import (
    MISSING_FROM_REPORT,
    ErrorCheck,
    compare_cli_errors,
    diff_file_ids_between_runs,
    diff_final_manifest,
    extract_error_from_log,
    file_ids_by_name,
    final_manifest_path,
    find_cli_log,
    find_column,
    format_checks_tsv,
    is_valid_file_id,
    latest_upload_report,
    load_expected_errors_by_file_name,
    normalize_error_cell,
    read_manifest,
    read_upload_report,
    strip_log_prefix,
    verify_cli_error_messages,
    verify_final_manifest,
    verify_final_manifest_deterministic,
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
        "Row 2: empty file_id",
        "Row 3: invalid file_id 'dg.4DFC/nope'",
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


def _manifest_run(tmp_path: Path, name: str, original: str, final: str | None) -> CliUpload:
    """A CliUpload whose manifest (and optionally its -final.tsv) are written under tmp_path."""
    folder = tmp_path / name
    folder.mkdir()
    manifest = folder / "manifest.tsv"
    manifest.write_text(original, encoding="utf-8")
    if final is not None:
        final_manifest_path(manifest).write_text(final, encoding="utf-8")
    return CliUpload(CliResult(0, ""), tmp_path, manifest, folder)


_ORIGINAL_TSV = "type\tfile_name\nfile\ta.txt\nfile\tb.csv\n"


def _final_tsv(id_a: str = _ID_A, id_b: str = _ID_B) -> str:
    return f"type\tfile_name\tfile_id\nfile\ta.txt\t{id_a}\nfile\tb.csv\t{id_b}\n"


def test_verify_final_manifest_passes(tmp_path: Path) -> None:
    verify_final_manifest(_manifest_run(tmp_path, "run1", _ORIGINAL_TSV, _final_tsv()))


def test_verify_final_manifest_lists_problems(tmp_path: Path) -> None:
    upload = _manifest_run(tmp_path, "run1", _ORIGINAL_TSV, _final_tsv(id_b="dg.4DFC/nope"))
    with pytest.raises(AssertionError, match="Row 3: invalid file_id 'dg.4DFC/nope'"):
        verify_final_manifest(upload)


def test_verify_final_manifest_fails_without_final_file(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="final manifest not found"):
        verify_final_manifest(_manifest_run(tmp_path, "run1", _ORIGINAL_TSV, None))


def test_verify_final_manifest_fails_without_manifest(tmp_path: Path) -> None:
    upload = CliUpload(CliResult(0, ""), tmp_path, None, tmp_path)
    with pytest.raises(AssertionError, match="no manifest"):
        verify_final_manifest(upload)


def test_verify_final_manifest_deterministic_passes(tmp_path: Path) -> None:
    first = _manifest_run(tmp_path, "run1", _ORIGINAL_TSV, _final_tsv())
    second = _manifest_run(tmp_path, "run2", _ORIGINAL_TSV, _final_tsv())
    verify_final_manifest_deterministic(first, second)


def test_verify_final_manifest_deterministic_fails_when_ids_change(tmp_path: Path) -> None:
    first = _manifest_run(tmp_path, "run1", _ORIGINAL_TSV, _final_tsv())
    second = _manifest_run(tmp_path, "run2", _ORIGINAL_TSV, _final_tsv(id_a=_ID_B))
    with pytest.raises(AssertionError, match="file_id differs between runs"):
        verify_final_manifest_deterministic(first, second)


def test_verify_final_manifest_deterministic_fails_without_second_final(tmp_path: Path) -> None:
    first = _manifest_run(tmp_path, "run1", _ORIGINAL_TSV, _final_tsv())
    second = _manifest_run(tmp_path, "run2", _ORIGINAL_TSV, None)
    with pytest.raises(AssertionError, match=r"second run.*final manifest not found"):
        verify_final_manifest_deterministic(first, second)


def test_verify_final_manifest_deterministic_fails_without_file_id_column(tmp_path: Path) -> None:
    first = _manifest_run(tmp_path, "run1", _ORIGINAL_TSV, _final_tsv())
    second = _manifest_run(tmp_path, "run2", _ORIGINAL_TSV, "type\tfile_name\nfile\ta.txt\n")
    with pytest.raises(AssertionError, match="needs a 'file_id' column"):
        verify_final_manifest_deterministic(first, second)


def _final_with_internal(rows: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    """Final manifest as the CLI writes it: basename in file_name, flattened path in internal_file_name."""
    return ["type", "file_name", "internal_file_name", "file_id"], rows


def test_file_ids_by_name_tells_apart_same_basename_in_different_folders() -> None:
    table = _final_with_internal([["file", "a.txt", "dirA_a.txt", _ID_A], ["file", "a.txt", "dirB_a.txt", _ID_B]])
    assert file_ids_by_name(table) == {"dirA_a.txt": _ID_A, "dirB_a.txt": _ID_B}


def test_file_ids_by_name_falls_back_to_file_name_without_internal_column() -> None:
    assert file_ids_by_name((["file_name", "file_id"], [["a.txt", _ID_A]])) == {"a.txt": _ID_A}


def test_diff_file_ids_between_runs_sees_a_changed_id_for_a_same_basename_file() -> None:
    first = _final_with_internal([["file", "a.txt", "dirA_a.txt", _ID_A], ["file", "a.txt", "dirB_a.txt", _ID_B]])
    second = _final_with_internal([["file", "a.txt", "dirA_a.txt", _ID_A], ["file", "a.txt", "dirB_a.txt", _ID_A]])
    assert diff_file_ids_between_runs(first, second) == [f"dirB_a.txt: first={_ID_B}, second={_ID_A}"]


SIZE_ERROR = "Real file size 8442 of file demo1.xlsx does not match with that in manifest 844!"
MD5_ERROR = "Real file md5 12bc of file demo2.pdf does not match with that in manifest 112bc!"


def test_find_column_is_case_insensitive_and_follows_candidate_order() -> None:
    assert find_column(["type", "File_Name", "Error"], ("errors", "error")) == 2
    assert find_column(["errors", "error"], ("error", "errors")) == 1
    assert find_column(["a", "b"], ("errors",)) == -1


def test_normalize_error_cell() -> None:
    assert normalize_error_cell("") == ""
    assert normalize_error_cell("[]") == ""
    assert normalize_error_cell(f"['{SIZE_ERROR}']") == SIZE_ERROR
    assert normalize_error_cell("['b', 'a']") == "a | b"
    assert normalize_error_cell('"plain ""quoted"" message"') == 'plain "quoted" message'
    assert normalize_error_cell("single message") == "single message"


def test_load_expected_errors_by_file_name(tmp_path: Path) -> None:
    (tmp_path / "a.tsv").write_text(
        f"type\texpected_errors\tfile_name\nfile\t['{SIZE_ERROR}']\tdemo1.xlsx\nfile\t\tdemo3.txt\n", encoding="utf-8"
    )
    (tmp_path / "b.tsv").write_text("expected_error\tinternal_file_name\nmsg\tdemo2.pdf\n", encoding="utf-8")
    (tmp_path / "no-columns.tsv").write_text("a\tb\n1\t2\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("x", encoding="utf-8")
    assert load_expected_errors_by_file_name(tmp_path) == {
        "demo1.xlsx": f"['{SIZE_ERROR}']",
        "demo3.txt": "",
        "demo2.pdf": "msg",
    }
    assert load_expected_errors_by_file_name(tmp_path / "missing") == {}


def _write_report(cli_dir: Path, name: str = "upload-report-1.tsv", errors: dict[str, str] | None = None) -> Path:
    tmp = cli_dir / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    rows = errors if errors is not None else {"demo1.xlsx": f"['{SIZE_ERROR}']", "demo3.txt": ""}
    lines = ["file_name\tfile_size\tsucceeded\terrors"]
    lines += [f"{file}\t10\tFalse\t{error}" for file, error in rows.items()]
    path = tmp / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_latest_upload_report_picks_the_newest(tmp_path: Path) -> None:
    old = _write_report(tmp_path, "upload-report-1.tsv")
    new = _write_report(tmp_path, "upload-report-2.tsv")
    os.utime(old, (1, 1))
    os.utime(new, (2, 2))
    assert latest_upload_report(tmp_path) == new
    with pytest.raises(AssertionError, match="No upload-report"):
        latest_upload_report(tmp_path / "empty")


def test_read_upload_report(tmp_path: Path) -> None:
    report = _write_report(tmp_path)
    assert read_upload_report(report) == [("demo1.xlsx", f"['{SIZE_ERROR}']"), ("demo3.txt", "")]


def test_read_upload_report_reads_a_quoted_cell_with_a_tab_in_it(tmp_path: Path) -> None:
    report = tmp_path / "r.tsv"
    report.write_text('file_name\terrors\ndemo.txt\t"bad\tcell"\n', encoding="utf-8")
    assert read_upload_report(report) == [("demo.txt", "bad\tcell")]


def test_read_upload_report_rejects_empty_and_missing_columns(tmp_path: Path) -> None:
    empty = tmp_path / "empty.tsv"
    empty.write_text("file_name\terrors\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="no data rows"):
        read_upload_report(empty)
    no_errors = tmp_path / "no-errors.tsv"
    no_errors.write_text("file_name\tx\na\tb\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="no errors column"):
        read_upload_report(no_errors)
    no_name = tmp_path / "no-name.tsv"
    no_name.write_text("errors\tx\na\tb\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="no file name column"):
        read_upload_report(no_name)


def test_strip_log_prefix_starts_at_the_error_phrase() -> None:
    line = "<14>1 2026-03-04T17:05:03.059Z - - 35293 - - ERROR: (File_Validator) Real file md5 abc of file x does not match"
    assert strip_log_prefix(line) == "Real file md5 abc of file x does not match"
    assert strip_log_prefix("  plain line  ") == "plain line"


def test_extract_error_from_log_by_file_name_then_single_file_fallback() -> None:
    log_text = "\n".join(
        [
            "INFO starting",
            "ERROR Real file size 1 of file other.txt does not match with that in manifest 2!",
            "ERROR Real file md5 abc of file demo2.pdf does not match with that in manifest def!",
        ]
    )
    assert "demo2.pdf" in extract_error_from_log("demo2.pdf", log_text)
    assert "demo2" in extract_error_from_log("demo2.csv", log_text)  # name without extension
    assert extract_error_from_log("nothing.zip", log_text) == ""
    assert extract_error_from_log("nothing.zip", log_text, single_file_fallback=True).startswith(
        "ERROR Real file size 1"
    )
    assert extract_error_from_log("", log_text) == "" and extract_error_from_log("a", "") == ""


def test_find_cli_log_picks_the_log_closest_to_the_report(tmp_path: Path) -> None:
    report = _write_report(tmp_path)
    os.utime(report, (100, 100))
    near = tmp_path / "tmp" / "near.log"
    far = tmp_path / "tmp" / "far.log"
    near.write_text("n", encoding="utf-8")
    far.write_text("f", encoding="utf-8")
    os.utime(near, (101, 101))
    os.utime(far, (500, 500))
    assert find_cli_log(tmp_path, report) == near
    near.unlink()
    far.unlink()
    assert find_cli_log(tmp_path, report) is None


def test_compare_cli_errors_matches_and_flags_differences() -> None:
    rows = [("demo1.xlsx", f"['{SIZE_ERROR}']"), ("demo2.pdf", f"['{MD5_ERROR}']"), ("demo3.txt", "")]
    expected = {"demo1.xlsx": f"['{SIZE_ERROR}']", "demo2.pdf": "['something else']", "demo3.txt": ""}
    checks = compare_cli_errors(rows, expected)
    assert [check.ok for check in checks] == [True, False, True]
    assert checks[1] == ErrorCheck("demo2.pdf", MD5_ERROR, "something else")


def test_compare_cli_errors_fails_a_flagged_file_nobody_expected() -> None:
    checks = compare_cli_errors([("extra.txt", "['boom']")], {"demo1.xlsx": "x"})
    assert not checks[0].ok and checks[0].expected == ""


def test_compare_cli_errors_fails_a_file_with_expected_errors_that_is_not_in_the_report() -> None:
    rows = [("demo3.txt", "")]
    expected = {"demo1.xlsx": f"['{SIZE_ERROR}']", "demo3.txt": ""}
    checks = compare_cli_errors(rows, expected)
    assert [check.ok for check in checks] == [True, False]
    assert checks[1] == ErrorCheck("demo1.xlsx", MISSING_FROM_REPORT, SIZE_ERROR)


def test_compare_cli_errors_ignores_a_missing_file_that_expects_no_errors() -> None:
    checks = compare_cli_errors([("demo1.xlsx", "")], {"demo1.xlsx": "", "demo3.txt": "[]"})
    assert [check.file_name for check in checks] == ["demo1.xlsx"] and checks[0].ok


def test_compare_cli_errors_takes_an_empty_cell_from_the_log() -> None:
    log_text = f"<14>1 2026-03-04T17:05:03Z - - 1 - - ERROR: (File_Validator) {MD5_ERROR}"
    checks = compare_cli_errors([("demo2.pdf", "")], {"demo2.pdf": f"['{MD5_ERROR}']"}, log_text)
    assert checks[0].ok and checks[0].actual == MD5_ERROR


def test_format_checks_tsv() -> None:
    text = format_checks_tsv([ErrorCheck("a.txt", "x\ty", "x\ty"), ErrorCheck("b.txt", "p", "q")])
    assert text.splitlines() == [
        "file_name\tactual_error\texpected_error\tmatch_status",
        "a.txt\tx y\tx y\tPASS",
        "b.txt\tp\tq\tFAIL",
    ]


def _upload(tmp_path: Path) -> CliUpload:
    return CliUpload(result=CliResult(1, ""), data_dir=tmp_path / "data", manifest=None, cli_work_dir=tmp_path / "cli")


def _expected_folder(root: Path, tc: str, text: str) -> None:
    folder = root / "InputFiles" / "CRDC" / "MetadataData" / tc / "expected"
    folder.mkdir(parents=True)
    (folder / "expected.tsv").write_text(text, encoding="utf-8")


def test_verify_cli_error_messages_passes_and_writes_a_report(tmp_path: Path) -> None:
    _write_report(tmp_path / "cli")
    _expected_folder(tmp_path, "TC", f"expected_errors\tfile_name\n['{SIZE_ERROR}']\tdemo1.xlsx\n\tdemo3.txt\n")
    out = tmp_path / "out"
    checks = verify_cli_error_messages(_upload(tmp_path), "TC", root=tmp_path, report_dir=out)
    assert [check.ok for check in checks] == [True, True]
    reports = list(out.glob("error-verification-TC-*.tsv"))
    assert len(reports) == 1 and "demo1.xlsx" in reports[0].read_text(encoding="utf-8")


def test_verify_cli_error_messages_fails_on_a_mismatch_with_both_values(tmp_path: Path) -> None:
    _write_report(tmp_path / "cli")
    _expected_folder(tmp_path, "TC", "expected_errors\tfile_name\n['different']\tdemo1.xlsx\n")
    with pytest.raises(AssertionError, match=r"(?s)mismatch.*demo1\.xlsx.*different"):
        verify_cli_error_messages(_upload(tmp_path), "TC", root=tmp_path, report_dir=tmp_path / "out")


def test_verify_cli_error_messages_fails_when_an_expected_file_is_missing_from_the_report(tmp_path: Path) -> None:
    _write_report(tmp_path / "cli")  # rows: demo1.xlsx, demo3.txt
    _expected_folder(
        tmp_path,
        "TC",
        f"expected_errors\tfile_name\n['{SIZE_ERROR}']\tdemo1.xlsx\n['{MD5_ERROR}']\tdemo2.pdf\n",
    )
    with pytest.raises(AssertionError, match=r"(?s)demo2\.pdf.*not in upload report"):
        verify_cli_error_messages(_upload(tmp_path), "TC", root=tmp_path, report_dir=tmp_path / "out")


def test_verify_cli_error_messages_fails_without_expected_tsvs_or_report(tmp_path: Path) -> None:
    _write_report(tmp_path / "cli")
    with pytest.raises(AssertionError, match="No expected TSV"):
        verify_cli_error_messages(_upload(tmp_path), "TC", root=tmp_path, report_dir=tmp_path / "out")
    with pytest.raises(AssertionError, match="No upload-report"):
        verify_cli_error_messages(
            CliUpload(CliResult(1, ""), tmp_path, None, tmp_path / "nowhere"), "TC", root=tmp_path
        )
