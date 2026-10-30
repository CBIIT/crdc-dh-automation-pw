"""Validation Results expected-TSV oracle (Katalon DataSubmissions VR compare).

Discovers InputFiles/CRDC/MetadataData/<tc>/expected-ValidationResults TSVs,
maps node → submitted-id column from DSV_ValidationResults-mappings.xlsx,
and diffs UI rows to expected by submitted identifier. Pages filter and read;
this module does not click Hub.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from openpyxl import load_workbook

from crdc_pw.locators.loader import repo_root

log = logging.getLogger("crdc_pw.validation_results")

METADATA_RELATIVE = Path("InputFiles/CRDC/MetadataData")
MAPPINGS_RELATIVE = Path("InputFiles/CRDC/DataSubmissionValidation/DSV_ValidationResults-mappings.xlsx")

# GC_diagnosis_v11.0.3.tsv → strip this suffix before taking the node name
_VERSION_SUFFIX = re.compile(r"_v\d+\.\d+\.\d+$")
_EXPECTED_SUFFIX = "_expected-ValidationResults.tsv"


def metadata_dir(tc_name: str, root: Path | None = None) -> Path:
    """InputFiles/CRDC/MetadataData/<tcName>."""
    return (root or repo_root()) / METADATA_RELATIVE / tc_name


def expected_dir(tc_name: str, root: Path | None = None) -> Path:
    """InputFiles/CRDC/MetadataData/<tcName>/expected-ValidationResults."""
    return metadata_dir(tc_name, root) / "expected-ValidationResults"


def mappings_path(root: Path | None = None) -> Path:
    """Committed node → submitted-id column workbook."""
    return (root or repo_root()) / MAPPINGS_RELATIVE


def node_from_filename(filename: str) -> str:
    """Node from an upload TSV name: strip .tsv and _vX.Y.Z, then after first _.

    GC_diagnosis_v11.0.3.tsv → diagnosis.
    """
    if not filename.endswith(".tsv"):
        return Path(filename).stem
    base = filename[: -len(".tsv")]
    base = _VERSION_SUFFIX.sub("", base)
    return base[base.index("_") + 1 :] if "_" in base else base


def node_from_expected_validation_results_filename(filename: str) -> str:
    """Node from GC_diagnosis_v11.0.3_expected-ValidationResults.tsv → diagnosis."""
    if not filename.endswith(_EXPECTED_SUFFIX):
        return ""
    base = filename[: -len(_EXPECTED_SUFFIX)]
    base = _VERSION_SUFFIX.sub("", base)
    return base[base.index("_") + 1 :] if "_" in base else base


def list_tsv_files_and_nodes_for_tc(tc_name: str, root: Path | None = None) -> tuple[list[Path], list[str]]:
    """Top-level *.tsv in the TC folder (not expected-ValidationResults)."""
    folder = metadata_dir(tc_name, root)
    if not folder.is_dir():
        raise FileNotFoundError(f"uploadFolder: folder not found or not a directory: {folder}")
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix == ".tsv")
    if not files:
        raise FileNotFoundError(f"uploadFolder: no .tsv files in {folder}")
    nodes = [node_from_filename(p.name) for p in files]
    return files, nodes


def load_validation_results_mappings(model: str, root: Path | None = None) -> dict[str, str]:
    """Node → submitted-identifier column from the model sheet (GC, ICDC, CTDC, PSDC).

    Tests pass model (GC) instead of inferring it from the pytest node id.
    GC diagnosis maps to study_diagnosis_id.
    """
    sheet_name = model.strip().upper()
    path = mappings_path(root)
    node_to_column: dict[str, str] = {}
    if not path.is_file():
        log.warning("Not able to get mapping from %s — file missing", path)
        return node_to_column
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet_name not in wb.sheetnames:
            log.warning("Sheet not found: %s", sheet_name)
            return node_to_column
        ws = wb[sheet_name]
        for row in ws.iter_rows(values_only=True):
            if not row or row[0] is None or (len(row) < 2 or row[1] is None):
                continue
            node_val = str(row[0]).strip()
            col_val = str(row[1]).strip()
            if node_val and col_val:
                node_to_column[node_val] = col_val
    finally:
        wb.close()
    log.info("Loading ValidationResults-Mappings from Excel. Sheet: %s", sheet_name)
    return node_to_column


def find_expected_validation_results_tsv(tc_name: str, node: str, root: Path | None = None) -> Path | None:
    """Expected TSV for this node, or None if the folder/file is missing."""
    folder = expected_dir(tc_name, root)
    if not folder.is_dir():
        return None
    for path in folder.iterdir():
        if path.is_file() and path.name.endswith(_EXPECTED_SUFFIX):
            if node_from_expected_validation_results_filename(path.name) == node:
                return path
    return None


def list_nodes_from_expected_validation_results_folder(tc_name: str, root: Path | None = None) -> list[str]:
    """Unique node names from *_expected-ValidationResults.tsv files, folder order."""
    folder = expected_dir(tc_name, root)
    log.info("verifyValidationResultsVsExpectedForTC: looking in %s", folder)
    if not folder.is_dir():
        log.info("verifyValidationResultsVsExpectedForTC: folder does not exist or is not a directory.")
        return []
    nodes: list[str] = []
    seen: set[str] = set()
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.name.endswith(_EXPECTED_SUFFIX))
    if not files:
        log.info("verifyValidationResultsVsExpectedForTC: no *_expected-ValidationResults.tsv files found.")
    for path in files:
        node = node_from_expected_validation_results_filename(path.name)
        if node and node not in seen:
            seen.add(node)
            nodes.append(node)
    return nodes


def _read_tsv_lines(path: Path) -> list[str]:
    """UTF-8 lines with the newline stripped. Empty file is an empty list."""
    return path.read_text(encoding="utf-8").splitlines()


def unique_severity_issue_type_pairs_from_expected_tsv(tsv_path: Path) -> list[tuple[str, str]]:
    """Unique (Expected_Severity, Issue_Type) pairs; skip blank severity or issue.

    Each pair becomes one UI filter + compare in verify_validation_results_vs_expected_for_tc.
    """
    out: list[tuple[str, str]] = []
    if not tsv_path.is_file():
        return out
    lines = _read_tsv_lines(tsv_path)
    if len(lines) < 2:
        return out
    headers = [h.strip() for h in lines[0].split("\t")]
    try:
        idx_issue = headers.index("Issue_Type")
        idx_sev = headers.index("Expected_Severity")
    except ValueError:
        return out
    seen: set[str] = set()
    for line in lines[1:]:
        cells = line.split("\t")
        row_issue = cells[idx_issue].strip() if idx_issue < len(cells) else ""
        row_sev = cells[idx_sev].strip() if idx_sev < len(cells) else ""
        if not row_sev or not row_issue:
            continue
        key = f"{row_sev}\t{row_issue}"
        if key not in seen:
            seen.add(key)
            out.append((row_sev, row_issue))
    return out


def load_expected_validation_results_tsv(
    tsv_path: Path,
    submitted_identifier_column: str,
    severity: str,
    issue_type: str,
) -> list[tuple[str, str, str]]:
    """Rows matching severity (case-insensitive) and issue type: (submitted_id, issue, severity).

    submitted_identifier_column comes from the mappings sheet (study_diagnosis_id for diagnosis).
    Issue_Type is an exact match. Expected_Severity ignores case.
    """
    out: list[tuple[str, str, str]] = []
    if not tsv_path.is_file():
        return out
    lines = _read_tsv_lines(tsv_path)
    if len(lines) < 2:
        return out
    headers = [h.strip() for h in lines[0].split("\t")]
    idx_id = idx_issue = idx_sev = -1
    for i, header in enumerate(headers):
        if header.lower() == submitted_identifier_column.lower():
            idx_id = i
        if header == "Issue_Type":
            idx_issue = i
        if header == "Expected_Severity":
            idx_sev = i
    if idx_id < 0 or idx_issue < 0 or idx_sev < 0:
        return out
    for line in lines[1:]:
        cells = line.split("\t")
        row_issue = cells[idx_issue].strip() if idx_issue < len(cells) else ""
        row_sev = cells[idx_sev].strip() if idx_sev < len(cells) else ""
        if row_issue != issue_type or row_sev.lower() != severity.lower():
            continue
        submitted_id = cells[idx_id].strip() if idx_id < len(cells) else ""
        out.append((submitted_id, row_issue, row_sev))
    return out


def diff_validation_results(
    expected_rows: list[tuple[str, str, str]],
    actual_rows: list[tuple[str, str, str]],
    issue_type: str,
) -> list[str]:
    """Katalon verifyValidationResultsVsExpected matching. Empty list means Pass.

    Match on submitted id. Duplicate UI ids keep the last row unless a row's
    issue type equals the current filter. Missing UI id = fail; extra UI id =
    fail; issue exact; severity case-insensitive.
    """
    actual_by_id: dict[str, tuple[str, str, str]] = {}
    for row in actual_rows:
        if not row or not (row[0] or "").strip():
            continue
        submitted_id = row[0].strip()
        act_issue = row[1] if len(row) >= 2 else ""
        if submitted_id not in actual_by_id or act_issue == issue_type:
            actual_by_id[submitted_id] = row
    errors: list[str] = []
    expected_ids = {exp[0] for exp in expected_rows}
    for submitted_id, exp_issue, exp_sev in expected_rows:
        act = actual_by_id.get(submitted_id)
        if act is None:
            errors.append(f"Submitted Identifier '{submitted_id}': expected in UI but not found")
            continue
        act_issue = act[1] if len(act) >= 2 else ""
        act_sev = act[2] if len(act) >= 3 else ""
        if act_issue != exp_issue:
            errors.append(
                f"Submitted Identifier '{submitted_id}': Issue Type expected '{exp_issue}', actual '{act_issue}'"
            )
        if act_sev.lower() != exp_sev.lower():
            errors.append(
                f"Submitted Identifier '{submitted_id}': Severity expected '{exp_sev}', actual '{act_sev}'"
            )
    for submitted_id in actual_by_id:
        if submitted_id not in expected_ids:
            errors.append(f"Submitted Identifier '{submitted_id}': present in UI but not in expected TSV")
    return errors
