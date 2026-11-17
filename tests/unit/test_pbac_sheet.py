"""No-browser checks that PBACPermissions.xlsx drives expected rows and Pass/Fail compare.

Does not open Hub. Copies the committed xlsx into a temp tree so OutputFiles stay off the repo.

Flow (this file):
  1. Fedlead column loads from the committed workbook
  2. Matching UI rows vs that column are all Pass
  3. One wrong checkbox state is Fail
  4. Each role's positive sheet selects its checked keys and role-specific permissions
  5. Each role's negative sheet selects unchecked / fixed_unchecked keys
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from openpyxl import load_workbook

from crdc_pw.locators.loader import repo_root
from crdc_pw.utils.pbac_sheet import (
    INPUT_RELATIVE,
    compare_actual,
    list_internal_names_for_scenario,
    load_expected_rows,
    output_path,
    write_expected,
)


def _temp_input_tree(tmp_path: Path) -> Path:
    dest = tmp_path / INPUT_RELATIVE
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(repo_root() / INPUT_RELATIVE, dest)
    return tmp_path


@pytest.mark.unit
def test_fedlead_column_loads_from_committed_xlsx() -> None:
    """Sheet Permissions has a Fedlead column; first row is Submission Request View, fixed_checked."""
    rows = load_expected_rows("Fedlead")
    assert len(rows) >= 40
    internal, expected, display = rows[0]
    assert internal == "submission_request:view"
    assert expected == "fixed_checked"
    assert display == "View"


@pytest.mark.unit
def test_dcp_and_admin_columns_load_from_committed_xlsx() -> None:
    """Dcp and Admin default columns exist for TC02/TC03."""
    dcp = load_expected_rows("Dcp")
    admin = load_expected_rows("Admin")
    assert len(dcp) >= 40
    assert len(admin) >= 40
    assert dcp[0][0] == admin[0][0] == "submission_request:view"


@pytest.mark.unit
def test_compare_matching_rows_all_pass(tmp_path: Path) -> None:
    """UI labels and statuses copied from the Fedlead column must all Pass."""
    root = _temp_input_tree(tmp_path)
    write_expected("Fedlead", root=root)
    expected = load_expected_rows("Fedlead", root=root)
    actual = [(display, status) for _internal, status, display in expected]
    assert compare_actual("Fedlead", actual, root=root)
    wb = load_workbook(output_path(root))
    ws = wb["Fedlead"]
    results = [ws.cell(row, 6).value for row in range(2, ws.max_row + 1)]
    assert results
    assert all(value == "Pass" for value in results)


@pytest.mark.unit
def test_compare_mismatched_state_fails(tmp_path: Path) -> None:
    """One checkbox with the wrong status marks that row Fail and the compare returns False."""
    root = _temp_input_tree(tmp_path)
    write_expected("Fedlead", root=root)
    expected = load_expected_rows("Fedlead", root=root)
    actual = [(display, status) for _internal, status, display in expected]
    label, _status = actual[0]
    actual[0] = (label, "unchecked")
    assert compare_actual("Fedlead", actual, root=root) is False
    wb = load_workbook(output_path(root))
    ws = wb["Fedlead"]
    assert ws.cell(2, 6).value == "Fail"
    assert ws.cell(2, 3).value == "unchecked"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("role", "checked_count", "has_admin_submit", "has_request_access", "ds_permissions"),
    [
        ("Fedlead", 40, False, False, {"view", "create", "cancel", "review", "confirm"}),
        ("Dcp", 40, True, False, {"view", "create", "cancel", "review", "admin_submit", "confirm"}),
        ("Admin", 43, True, False, {"view", "create", "cancel", "review", "admin_submit", "confirm"}),
        ("Submitter", 30, False, True, {"view", "create", "cancel"}),
        ("User", 18, False, True, set()),
    ],
)
def test_positive_functional_driver_lists_role_checked_keys(
    tmp_path: Path,
    role: str,
    checked_count: int,
    has_admin_submit: bool,
    has_request_access: bool,
    ds_permissions: set[str],
) -> None:
    """Each positive column selects the correct role's checked keys, including its DS and access scope."""
    root = _temp_input_tree(tmp_path)
    write_expected(f"{role}-positive", root=root)
    keys = list_internal_names_for_scenario(role, "positive", root=root)
    assert len(keys) == checked_count
    assert len(set(keys)) == checked_count
    assert "submission_request:view" in keys
    assert "submission_request:reopen" in keys
    assert ("data_submission:admin_submit" in keys) == has_admin_submit
    assert ("access:request" in keys) == has_request_access
    functional_ds_keys = {
        f"data_submission:{action}"
        for action in ("view", "create", "cancel", "review", "admin_submit", "confirm")
    }
    assert set(keys) & functional_ds_keys == {f"data_submission:{action}" for action in ds_permissions}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("role", "key_count", "has_admin_submit", "has_request_access", "has_sr_view", "ds_permissions"),
    [
        ("Fedlead", 43, True, True, True, {"view", "create", "cancel", "review", "admin_submit", "confirm"}),
        ("Dcp", 43, True, True, True, {"view", "create", "cancel", "review", "admin_submit", "confirm"}),
        ("Admin", 43, True, True, True, {"view", "create", "cancel", "review", "admin_submit", "confirm"}),
        ("Submitter", 14, True, False, False, {"review", "admin_submit", "confirm"}),
        ("User", 26, True, False, False, {"view", "create", "cancel", "review", "admin_submit", "confirm"}),
    ],
)
def test_negative_functional_driver_lists_role_unchecked_keys(
    tmp_path: Path,
    role: str,
    key_count: int,
    has_admin_submit: bool,
    has_request_access: bool,
    has_sr_view: bool,
    ds_permissions: set[str],
) -> None:
    """Each negative column selects unchecked / fixed_unchecked keys, including locked-off DS and access."""
    root = _temp_input_tree(tmp_path)
    write_expected(f"{role}-negative", root=root)
    keys = list_internal_names_for_scenario(role, "negative", root=root)
    assert len(keys) == key_count
    assert len(set(keys)) == key_count
    expected_rows = load_expected_rows(f"{role}-negative", root=root)
    assert any(status == "fixed_unchecked" for _internal, status, _display in expected_rows)
    assert ("submission_request:view" in keys) == has_sr_view
    assert ("submission_request:create" in keys) == has_sr_view
    assert ("submission_request:reopen" in keys) == has_sr_view
    assert ("data_submission:admin_submit" in keys) == has_admin_submit
    assert ("access:request" in keys) == has_request_access
    functional_ds_keys = {
        f"data_submission:{action}"
        for action in ("view", "create", "cancel", "review", "admin_submit", "confirm")
    }
    assert set(keys) & functional_ds_keys == {f"data_submission:{action}" for action in ds_permissions}
