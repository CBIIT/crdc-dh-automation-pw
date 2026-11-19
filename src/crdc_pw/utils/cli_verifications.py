"""Checks on what an upload CLI run produced (Katalon CliUploader verify keywords).

Katalon keeps these in CliUploader.groovy next to uploadFilesViaCli. Here the runner is
cli_uploader.py and the checks are this module. The pure functions read and compare files as plain
tables and are unit tested; nothing here runs the CLI or touches Hub.

Final manifest (Katalon verifyFinalManifest and verifyFinalManifestDeterministic): when the original
manifest has no file_id column the CLI writes <name>-final.tsv with a file_id per row.
  verify_final_manifest and verify_final_manifest_deterministic are the keywords a test calls; they use
  final_manifest_path, read_manifest, diff_final_manifest and diff_file_ids_between_runs (public for tests).

Error messages (Katalon verifyCliErrorMessages): after a CLI run that is expected to find invalid
files, the CLI's upload report (tmp/upload-report-*.tsv in its working directory) has one row per
file with an errors column. These are compared, by file name, with the expected_errors column of
InputFiles/CRDC/MetadataData/<tc>/expected/*.tsv. When the report's errors cell is empty for a file,
the error line for that file is taken from the CLI log (tmp/*.log), as in Katalon.
  verify_cli_error_messages is the keyword a test calls; the helpers it uses are public for tests.
"""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.cli_uploader import CliUpload
from crdc_pw.utils.validation_results import (
    expected_upload_errors_dir,
    parse_expected_errors_cell,
    read_tsv_lines,
)

log = logging.getLogger("crdc_pw.cli_verifications")

# Column that names the file, first one present wins (Katalon FILE_NAME_COLUMN_CANDIDATES).
FILE_NAME_COLUMNS = ("file_name", "internal_file_name", "fileName")


def find_column(headers: list[str], candidates: tuple[str, ...]) -> int:
    """Index of the first candidate that is a header (case-insensitive, candidates in order), else -1."""
    lowered = [header.strip().lower() for header in headers]
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered.index(candidate.lower())
    return -1


# ---------------------------------------------------------------------------
# Final manifest
# ---------------------------------------------------------------------------

Table = tuple[list[str], list[list[str]]]

# dg.4DFC/<uuid> or a bare uuid, lowercase hex (Katalon DRS_ID_WITH_PREFIX and BARE_UUID).
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_DRS_ID_WITH_PREFIX = re.compile(rf"^dg\.4DFC/{_UUID}$")
_BARE_UUID = re.compile(rf"^{_UUID}$")

FILE_ID_COLUMN = "file_id"


def final_manifest_path(manifest: Path) -> Path:
    """<name>-final.tsv beside the manifest, the way the CLI names it."""
    return manifest.with_name(manifest.name.replace(".tsv", "-final.tsv"))


def read_manifest(path: Path) -> Table:
    """(headers, rows) of a tab-separated manifest. Blank lines are skipped and cells are trimmed."""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return [], []
    headers = [cell.strip() for cell in lines[0].split("\t")]
    rows = [[cell.strip() for cell in line.split("\t")] for line in lines[1:]]
    return headers, rows


def is_valid_file_id(value: str) -> bool:
    """True for dg.4DFC/<uuid> or a bare uuid."""
    return bool(_DRS_ID_WITH_PREFIX.match(value) or _BARE_UUID.match(value))


def diff_final_manifest(original: Table, final: Table) -> list[str]:
    """Problems with the final manifest; empty means it is what the CLI should have written.

    The final manifest must have data rows, the same row count as the original, a file_id column,
    and a valid DRS id (dg.4DFC/<uuid> or bare uuid) in every row.
    """
    _original_headers, original_rows = original
    final_headers, final_rows = final
    if not final_rows:
        return ["Final manifest has no data rows"]
    problems: list[str] = []
    if len(final_rows) != len(original_rows):
        problems.append(f"Row count expected {len(original_rows)}, actual {len(final_rows)}")
    id_index = find_column(final_headers, (FILE_ID_COLUMN,))
    if id_index < 0:
        problems.append(f"Final manifest has no {FILE_ID_COLUMN!r} column")
        return problems
    # Katalon labels rows by file line number: the header is line 1, so the first data row is "Row 2"
    for number, row in enumerate(final_rows, start=2):
        value = row[id_index] if id_index < len(row) else ""
        if not value:
            problems.append(f"Row {number}: empty {FILE_ID_COLUMN}")
        elif not is_valid_file_id(value):
            problems.append(f"Row {number}: invalid {FILE_ID_COLUMN} {value!r}")
    return problems


def file_ids_by_name(table: Table) -> dict[str, str]:
    """file name -> file_id for every row with a file name. Raises ValueError without both columns."""
    headers, rows = table
    id_index = find_column(headers, (FILE_ID_COLUMN,))
    name_index = find_column(headers, FILE_NAME_COLUMNS)
    if id_index < 0 or name_index < 0:
        raise ValueError(f"Manifest needs a {FILE_ID_COLUMN!r} column and one of {FILE_NAME_COLUMNS}")
    ids: dict[str, str] = {}
    for row in rows:
        name = row[name_index] if name_index < len(row) else ""
        if name:
            ids[name] = row[id_index] if id_index < len(row) else ""
    return ids


def diff_file_ids_between_runs(first: Table, second: Table) -> list[str]:
    """Problems between two runs of the same upload; empty means every file got the same file_id.

    Files are matched by name. A file in only one run, or with a different id, is a problem.
    """
    first_ids = file_ids_by_name(first)
    second_ids = file_ids_by_name(second)
    if not first_ids:
        return ["First final manifest has no file name and file_id pairs"]
    problems: list[str] = []
    for name, first_id in first_ids.items():
        if name not in second_ids:
            problems.append(f"{name}: missing in second manifest")
        elif second_ids[name] != first_id:
            problems.append(f"{name}: first={first_id}, second={second_ids[name]}")
    for name in second_ids:
        if name not in first_ids:
            problems.append(f"{name}: missing in first manifest (extra in second)")
    return problems


def _read_final_manifest(upload: CliUpload, what: str) -> Table:
    """Final manifest the CLI wrote for this run; fails when it is missing."""
    assert upload.manifest is not None, f"{what}: the upload has no manifest (metadata upload?)"
    path = final_manifest_path(upload.manifest)
    assert path.is_file(), f"{what}: final manifest not found: {path}"
    return read_manifest(path)


def verify_final_manifest(upload: CliUpload) -> None:
    """Katalon verifyFinalManifest: the run's -final.tsv has a file_id column, a valid id in every
    row and the same row count as the manifest the CLI was given. Fails with every problem found."""
    assert upload.manifest is not None, "verify_final_manifest: the upload has no manifest"
    original = read_manifest(upload.manifest)
    final = _read_final_manifest(upload, "verify_final_manifest")
    log.info("Original manifest headers %s, %s rows", original[0], len(original[1]))
    log.info("Final manifest headers %s, %s rows", final[0], len(final[1]))
    problems = diff_final_manifest(original, final)
    assert not problems, "Final manifest problems:\n" + "\n".join(problems)
    log.info("Assert final manifest has valid file_id values for all %s rows", len(final[1]))


def verify_final_manifest_deterministic(first: CliUpload, second: CliUpload) -> None:
    """Katalon verifyFinalManifestDeterministic: two uploads of the same files gave every file the
    same file_id. The caller runs the second upload (Katalon runs it inside the keyword)."""
    first_final = _read_final_manifest(first, "verify_final_manifest_deterministic (first run)")
    second_final = _read_final_manifest(second, "verify_final_manifest_deterministic (second run)")
    try:
        problems = diff_file_ids_between_runs(first_final, second_final)
    except ValueError as error:
        raise AssertionError(f"verify_final_manifest_deterministic: {error}") from error
    assert not problems, "file_id differs between runs:\n" + "\n".join(problems)
    log.info("Assert file_ids are identical across both runs")


# ---------------------------------------------------------------------------
# CLI error messages
# ---------------------------------------------------------------------------

ACTUAL_ERRORS_COLUMNS = ("errors", "error")
EXPECTED_ERRORS_COLUMNS = ("expected_errors", "expected_error")

# A CLI log line is an error line for a file when it has one of these (Katalon CLI_ERROR_LINE_SUBSTRINGS).
CLI_ERROR_LINE_SUBSTRINGS = (
    "does not match",
    "No archive manifest",
    "does not match with that in archive manifest",
    "Real file md5",
    "Real file size",
)

# Katalon logs the whole CLI log (lines cut to 500 chars) when a file's error could not be found; so does the failure message.
_MAX_LOG_LINE_CHARS = 500
_MAX_CELL_CHARS = 200
REPORT_SUBFOLDER = "CLI_ErrorVerification"


@dataclass(frozen=True)
class ErrorCheck:
    """One report row compared with its expected errors (both already normalized)."""

    file_name: str
    actual: str
    expected: str

    @property
    def ok(self) -> bool:
        return self.actual == self.expected


def normalize_error_cell(raw: str | None) -> str:
    """Errors cell as one comparable string: messages sorted and joined with " | ".

    Accepts a plain message, a quoted message, or a Python list text such as "['msg1', 'msg2']".
    A blank cell or an empty list gives "".
    """
    return " | ".join(sorted(parse_expected_errors_cell(raw)))


def load_expected_errors_by_file_name(folder: Path) -> dict[str, str]:
    """file name to expected_errors cell, from every .tsv in folder that has both columns.

    Files without an expected_errors (or expected_error) column or without a file name column are
    skipped. An empty or missing folder gives an empty dict.
    """
    expected: dict[str, str] = {}
    if not folder.is_dir():
        return expected
    for path in sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".tsv"):
        lines = read_tsv_lines(path)
        if len(lines) < 2:
            continue
        headers = lines[0].split("\t")
        error_index = find_column(headers, EXPECTED_ERRORS_COLUMNS)
        name_index = find_column(headers, FILE_NAME_COLUMNS)
        if error_index < 0 or name_index < 0:
            continue
        for line in lines[1:]:
            cells = line.split("\t")
            name = cells[name_index].strip() if name_index < len(cells) else ""
            if name:
                expected[name] = cells[error_index].strip() if error_index < len(cells) else ""
    return expected


def latest_upload_report(cli_work_dir: Path) -> Path:
    """The newest tmp/upload-report-*.tsv in the CLI working directory. Raises AssertionError when none."""
    tmp = cli_work_dir / "tmp"
    reports = (
        sorted(tmp.glob("upload-report-*.tsv"), key=lambda p: p.stat().st_mtime, reverse=True) if tmp.is_dir() else []
    )
    if not reports:
        raise AssertionError(f"No upload-report-*.tsv found in {tmp}")
    return reports[0]


def read_upload_report(report: Path) -> list[tuple[str, str]]:
    """(file name, errors cell) for every data row of an upload report.

    Raises AssertionError when the report has no data rows or lacks the file name or errors column.
    """
    with report.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))
    if len(rows) < 2:
        raise AssertionError(f"Upload report has no data rows: {report}")
    headers = rows[0]
    errors_index = find_column(headers, ACTUAL_ERRORS_COLUMNS)
    name_index = find_column(headers, FILE_NAME_COLUMNS)
    if errors_index < 0:
        raise AssertionError(
            f"Report has no errors column (tried {ACTUAL_ERRORS_COLUMNS}). Header: {headers} in {report.name}"
        )
    if name_index < 0:
        raise AssertionError(f"Report has no file name column (tried {FILE_NAME_COLUMNS}): {report.name}")
    out: list[tuple[str, str]] = []
    for cells in rows[1:]:
        name = cells[name_index].strip() if name_index < len(cells) else ""
        errors = cells[errors_index].strip() if errors_index < len(cells) else ""
        out.append((name, errors))
    return out


def find_cli_log(cli_work_dir: Path, report: Path) -> Path | None:
    """The .log in the CLI's tmp folder (or work dir) closest in time to the report, or None."""
    candidates = [p for folder in (cli_work_dir, cli_work_dir / "tmp") if folder.is_dir() for p in folder.glob("*.log")]
    if not candidates:
        return None
    report_time = report.stat().st_mtime
    return min(candidates, key=lambda p: abs(p.stat().st_mtime - report_time))


def strip_log_prefix(line: str) -> str:
    """Drop the syslog prefix of a CLI log line: start at the earliest error phrase in it.

    '<14>1 2026-03-04T17:05:03Z - - 35293 - - ERROR: (File_Validator) Real file md5 ...' gives
    'Real file md5 ...'. A line without an error phrase is only trimmed.
    """
    trimmed = line.strip()
    lowered = trimmed.lower()
    starts = [lowered.index(phrase.lower()) for phrase in CLI_ERROR_LINE_SUBSTRINGS if phrase.lower() in lowered]
    return trimmed[min(starts) :].strip() if starts else trimmed


def extract_error_from_log(file_name: str, log_text: str, single_file_fallback: bool = False) -> str:
    """The first log line that has an error phrase and names the file (or its name without extension).

    With single_file_fallback (the report has one row) a line with an error phrase and more than
    40 characters is used when none names the file. Returns "" when nothing matches.
    """
    if not file_name or not log_text:
        return ""
    base_name = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
    fallback = ""
    for raw in log_text.splitlines():
        line = raw.strip()
        if not line or not any(phrase.lower() in line.lower() for phrase in CLI_ERROR_LINE_SUBSTRINGS):
            continue
        if file_name in line or base_name in line:
            return line
        if single_file_fallback and len(line) > 40 and not fallback:
            fallback = line
    return fallback


def compare_cli_errors(
    report_rows: list[tuple[str, str]],
    expected_by_file: dict[str, str],
    log_text: str = "",
) -> list[ErrorCheck]:
    """Compare every report row with the expected errors for its file name.

    Where a row's errors cell is empty the error line for the file is taken from log_text. A file
    that is not in expected_by_file is expected to have no errors, so a row the CLI flagged that
    nobody expected fails.
    """
    checks: list[ErrorCheck] = []
    single = len(report_rows) == 1
    for file_name, actual_raw in report_rows:
        if not actual_raw and log_text:
            from_log = extract_error_from_log(file_name, log_text, single)
            if from_log:
                actual_raw = strip_log_prefix(from_log)
        checks.append(
            ErrorCheck(
                file_name=file_name,
                actual=normalize_error_cell(actual_raw),
                expected=normalize_error_cell(expected_by_file.get(file_name, "")),
            )
        )
    return checks


def _truncate(text: str, limit: int = _MAX_CELL_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + "..."


def format_checks_tsv(checks: list[ErrorCheck]) -> str:
    """The error verification report as TSV (Katalon error-verification-<tc>-<time>.tsv)."""
    lines = ["file_name\tactual_error\texpected_error\tmatch_status"]
    for check in checks:
        actual = check.actual.replace("\t", " ").replace("\n", " ").replace("\r", " ")
        expected = check.expected.replace("\t", " ").replace("\n", " ").replace("\r", " ")
        lines.append(f"{check.file_name}\t{actual}\t{expected}\t{'PASS' if check.ok else 'FAIL'}")
    return "\n".join(lines) + "\n"


def verify_cli_error_messages(
    upload: CliUpload,
    tc_name: str,
    *,
    root: Path | None = None,
    report_dir: Path | None = None,
) -> list[ErrorCheck]:
    """Assert the CLI's errors for each file are the expected ones (Katalon verifyCliErrorMessages).

    Reads the newest upload report from upload.cli_work_dir and the expected TSVs from
    InputFiles/CRDC/MetadataData/<tc_name>/expected/, logs expected and actual per file, and writes
    the TSV report to report_dir (default reports/CLI_ErrorVerification). Raises AssertionError when
    the report or expected files are missing or any file's errors differ. Returns the checks.
    """
    report = latest_upload_report(upload.cli_work_dir)
    rows = read_upload_report(report)
    folder = expected_upload_errors_dir(tc_name, root)
    expected = load_expected_errors_by_file_name(folder)
    if not expected:
        raise AssertionError(f"No expected TSV with expected_errors and file_name columns found in {folder}")
    log_file = find_cli_log(upload.cli_work_dir, report)
    log_text = log_file.read_text(encoding="utf-8", errors="replace") if log_file else ""
    log.info("CLI upload report %s, CLI log %s", report, log_file)

    checks = compare_cli_errors(rows, expected, log_text)
    for check in checks:
        log.info(
            "CLI errors for %s: %s\n  expected: %s\n  actual:   %s",
            check.file_name,
            "PASS" if check.ok else "FAIL",
            _truncate(check.expected),
            _truncate(check.actual),
        )

    folder_out = report_dir or (root or repo_root()) / "reports" / REPORT_SUBFOLDER
    folder_out.mkdir(parents=True, exist_ok=True)
    out = folder_out / f"error-verification-{tc_name}-{datetime.now():%Y%m%d_%H%M%S}.tsv"
    out.write_text(format_checks_tsv(checks), encoding="utf-8")
    log.info("CLI error verification report written to %s", out)

    mismatches = [
        f"{check.file_name}: actual={check.actual!r} vs expected={check.expected!r}" for check in checks if not check.ok
    ]
    if mismatches:
        lines = [_truncate(line, _MAX_LOG_LINE_CHARS) for line in log_text.splitlines()]
        context = ("\nCLI log:\n" + "\n".join(lines)) if lines and any(not c.actual for c in checks if not c.ok) else ""
        raise AssertionError("CLI error message mismatch(es):\n" + "\n".join(mismatches) + context)
    log.info("Assert CLI errors match expected for %s (%d files)", tc_name, len(checks))
    return checks
