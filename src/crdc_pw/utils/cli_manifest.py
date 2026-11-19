"""Oracles for the manifest the upload CLI writes next to the manifest it was given.

Katalon: CliUploader.verifyFinalManifest and verifyFinalManifestDeterministic. When the original
manifest has no file_id column the CLI writes <name>-final.tsv with a file_id per row. These
functions read and compare manifests as plain tables. They do not run the CLI or touch Hub.
"""

from __future__ import annotations

import re
from pathlib import Path

Table = tuple[list[str], list[list[str]]]

# dg.4DFC/<uuid> or a bare uuid, lowercase hex (Katalon DRS_ID_WITH_PREFIX and BARE_UUID).
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_DRS_ID_WITH_PREFIX = re.compile(rf"^dg\.4DFC/{_UUID}$")
_BARE_UUID = re.compile(rf"^{_UUID}$")

# Column that names the file, first one present wins (Katalon FILE_NAME_COLUMN_CANDIDATES).
FILE_NAME_COLUMNS = ("file_name", "internal_file_name", "fileName")
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


def _column_index(headers: list[str], names: tuple[str, ...] | str) -> int:
    """Index of the first of names found in headers (case-insensitive), or -1."""
    wanted = (names,) if isinstance(names, str) else names
    lowered = [h.lower() for h in headers]
    for name in wanted:
        if name.lower() in lowered:
            return lowered.index(name.lower())
    return -1


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
    id_index = _column_index(final_headers, FILE_ID_COLUMN)
    if id_index < 0:
        problems.append(f"Final manifest has no {FILE_ID_COLUMN!r} column")
        return problems
    for number, row in enumerate(final_rows, start=1):
        value = row[id_index] if id_index < len(row) else ""
        if not value:
            problems.append(f"Row {number}: empty {FILE_ID_COLUMN}")
        elif not is_valid_file_id(value):
            problems.append(f"Row {number}: invalid {FILE_ID_COLUMN} {value!r}")
    return problems


def file_ids_by_name(table: Table) -> dict[str, str]:
    """file name -> file_id for every row with a file name. Raises ValueError without both columns."""
    headers, rows = table
    id_index = _column_index(headers, FILE_ID_COLUMN)
    name_index = _column_index(headers, FILE_NAME_COLUMNS)
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
