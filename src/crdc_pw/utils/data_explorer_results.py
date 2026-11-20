"""Expected-TSV oracle for the Data Explorer study view (Katalon DataExplorer keywords).

Reads InputFiles/CRDC/MetadataData/<tc>/<node>.tsv (or <tc>/Metadata/<node>.tsv) and diffs it
with the table the study view shows. Pages read; this module does not click Hub.
"""

from __future__ import annotations

from pathlib import Path

from crdc_pw.utils.validation_results import metadata_dir, node_from_filename, read_tsv_lines


def find_expected_data_explorer_tsv(tc_name: str, node: str, root: Path | None = None) -> Path | None:
    """First TSV under <tc>/ then <tc>/Metadata/ for the node, ignoring case.

    Two names are accepted. The literal file name without .tsv (consent_group.tsv is consent_group)
    is tried first, in both folders, so an exact name always wins. Then the upload-style node from
    node_from_filename (GC_diagnosis_v11.0.3.tsv is diagnosis), which drops the text before the
    first underscore and so cannot find a plain name that contains an underscore.
    """
    base = metadata_dir(tc_name, root)
    wanted = node.strip().lower()
    paths = [
        path
        for folder in (base, base / "Metadata")
        if folder.is_dir()
        for path in sorted(folder.glob("*.tsv"))
    ]
    for path in paths:
        if path.stem.lower() == wanted:
            return path
    for path in paths:
        if node_from_filename(path.name).lower() == wanted:
            return path
    return None


def load_expected_data_explorer_table(
    tc_name: str, node: str, root: Path | None = None
) -> tuple[list[str], list[list[str]]]:
    """Expected (headers, rows) for a node.

    The type column and any column whose name has a dot (a relationship such as
    study.study_id) are dropped, because the UI table does not show them. Values are
    trimmed and unquoted. Rows are sorted by the first column ignoring case, which is the
    order the UI table uses. Raises FileNotFoundError when there is no TSV for the node.
    """
    path = find_expected_data_explorer_tsv(tc_name, node, root)
    if path is None:
        raise FileNotFoundError(f"No expected TSV for node {node!r} under {metadata_dir(tc_name, root)}")
    lines = read_tsv_lines(path)
    if not lines:
        return [], []
    raw_headers = [h.strip() for h in lines[0].split("\t")]
    kept = [i for i, h in enumerate(raw_headers) if h.lower() != "type" and "." not in h]
    headers = [raw_headers[i] for i in kept]
    rows: list[list[str]] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = line.split("\t")
        row = []
        for i in kept:
            value = cells[i].strip() if i < len(cells) else ""
            if len(value) > 1 and value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            row.append(value)
        rows.append(row)
    rows.sort(key=lambda row: row[0].lower() if row else "")
    return headers, rows


def map_expected_headers_to_ui(expected_headers: list[str], ui_headers: list[str]) -> list[int]:
    """UI column index for each expected header, or -1. Equal ignoring case, with _ read as a space."""
    mapping: list[int] = []
    for exp in expected_headers:
        want = exp.replace("_", " ").strip().lower()
        index = -1
        for i, ui in enumerate(ui_headers):
            if ui.lower() == exp.lower() or ui.replace("_", " ").strip().lower() == want:
                index = i
                break
        mapping.append(index)
    return mapping


def diff_data_explorer_table(
    expected_headers: list[str],
    expected_rows: list[list[str]],
    ui_headers: list[str],
    ui_rows: list[list[str]],
) -> list[str]:
    """Mismatch messages; empty means the UI table matches the expected one.

    Checks the row count, that every expected header is in the UI, and (when the row count
    matches) every cell by row position. A cell matches when the texts are equal or the UI text
    contains the expected text with "..." removed (truncated values), as in Katalon. Unlike Katalon,
    an empty expected value only matches an empty UI value.
    """
    problems: list[str] = []
    if len(ui_rows) != len(expected_rows):
        problems.append(f"Row count expected {len(expected_rows)}, actual {len(ui_rows)}")
    mapping = map_expected_headers_to_ui(expected_headers, ui_headers)
    for header, index in zip(expected_headers, mapping):
        if index < 0:
            problems.append(f"Column {header!r} is missing in the UI table")
    if len(ui_rows) != len(expected_rows):
        return problems
    for r, (exp_row, act_row) in enumerate(zip(expected_rows, ui_rows), start=1):
        for c, exp in enumerate(exp_row):
            index = mapping[c] if c < len(mapping) else -1
            act = act_row[index].strip() if 0 <= index < len(act_row) else ""
            # Containment only for non-empty text: "" is in every string, so an empty expected value
            # must equal the UI value (Katalon lets any UI text pass here).
            cleaned = exp.replace("...", "").strip()
            if exp == act or (cleaned and cleaned in act):
                continue
            header = expected_headers[c] if c < len(expected_headers) else str(c + 1)
            problems.append(f"Row {r} column {header!r}: expected {exp!r}, actual {act!r}")
    return problems
