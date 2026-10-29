"""Unit tests for Excel DS Meta/Steps loader and step runner (no browser)."""

from __future__ import annotations

from pathlib import Path

import pytest

import shutil

from crdc_pw.config import Settings, load_settings, profile_paths
from crdc_pw.utils.excel_ds_test_runner.config_helpers import excel_ds_cases_glob, excel_ds_enabled
from crdc_pw.utils.excel_ds_test_runner.loader import ExcelLoadError, load_steps, read_meta_role
from crdc_pw.utils.excel_ds_test_runner.step_runner import run_testcase_excel
from crdc_pw.locators.loader import repo_root


def _write_minimal_excel_case(
    out_path: Path,
    *,
    role: str,
    input_root: str,
    steps: list[tuple[str, str, str]],
) -> None:
    """Minimal Meta + Steps workbook for loader/runner unit tests only."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Steps"
    ws.append(["Input Excel", "Action", "Params", "Model"])
    ws.append([input_root, None, None, None])
    for action, params, model in steps:
        ws.append([None, action, params, model])
    meta = wb.create_sheet("Meta")
    meta.append(["key", "value"])
    meta.append(["role", role])
    meta.append(["enabled", "Y"])
    wb.save(out_path)


@pytest.mark.unit
def test_tc08_committed_workbook_meta_and_steps() -> None:
    path = (
        repo_root()
        / "tests/DataValidation/GC/TC08_CRDC-VerifyInvalidIntegerValue.xlsx"
    )
    assert path.is_file(), path
    assert read_meta_role(path) == "Submitter"
    _input_root, steps = load_steps(path)
    assert _input_root.endswith("MetadataData/TC08")
    actions = [s.action for s in steps]
    assert actions == [
        "open_data_submissions",
        "create_data_submission",
        "upload_metadata_folder",
        "click_validate",
        "verify_validation_results_for_tc",
    ]


@pytest.mark.unit
def test_missing_steps_sheet_raises(tmp_path: Path) -> None:
    path = tmp_path / "TC99_bad.xlsx"
    _write_minimal_excel_case(
        path,
        role="Submitter",
        input_root="InputFiles/CRDC/MetadataData/TC08",
        steps=[("open_data_submissions", "", "")],
    )
    import openpyxl

    wb = openpyxl.load_workbook(path)
    del wb["Steps"]
    wb.save(path)
    with pytest.raises(ExcelLoadError, match="Steps"):
        load_steps(path)


@pytest.mark.unit
def test_invalid_role_in_meta_raises(tmp_path: Path) -> None:
    path = tmp_path / "TC99_role.xlsx"
    _write_minimal_excel_case(
        path,
        role="NotARealRole",
        input_root="InputFiles/CRDC/MetadataData/TC08",
        steps=[("open_data_submissions", "", "")],
    )
    with pytest.raises(ExcelLoadError, match="Invalid Meta role"):
        read_meta_role(path)


@pytest.mark.unit
def test_run_testcase_excel_dispatches_steps(tmp_path: Path) -> None:
    path = tmp_path / "TC99_run.xlsx"
    _write_minimal_excel_case(
        path,
        role="Submitter",
        input_root="InputFiles/CRDC/MetadataData/TC08",
        steps=[
            ("open_data_submissions", "", ""),
            (
                "create_data_submission",
                "New|metadata only|GC|autoQA - AutomationQA_Study",
                "",
            ),
            ("upload_metadata_folder", "TC08", ""),
            ("click_validate", "", ""),
            ("verify_validation_results_for_tc", "TC08", "GC"),
        ],
    )
    calls: list[tuple[str, ...]] = []

    class StubList:
        def open(self) -> None:
            calls.append(("open",))

        def create_data_submission(self, a: str, b: str, c: str, d: str) -> None:
            calls.append(("create", a, b, c, d))

    class StubDetail:
        def upload_folder(self, folder: str) -> None:
            calls.append(("upload", folder))

        def click_validate(self) -> None:
            calls.append(("validate",))

        def verify_validation_results_vs_expected_for_tc(self, tc: str, *, model: str) -> None:
            calls.append(("verify", tc, model))

    class StubHub:
        page = object()
        locators = object()

    import crdc_pw.utils.excel_ds_test_runner.step_runner as sr

    orig_list = sr.DataSubmissionsListPage
    orig_detail = sr.DataSubmissionDetailPage
    list_inst = StubList()
    detail_inst = StubDetail()
    sr.DataSubmissionsListPage = lambda *a, **k: list_inst  # type: ignore[misc, assignment]
    sr.DataSubmissionDetailPage = lambda *a, **k: detail_inst  # type: ignore[misc, assignment]
    try:
        run_testcase_excel(StubHub(), path)  # type: ignore[arg-type]
    finally:
        sr.DataSubmissionsListPage = orig_list
        sr.DataSubmissionDetailPage = orig_detail

    assert calls[0] == ("open",)
    assert calls[1] == ("create", "New", "metadata only", "GC", "autoQA - AutomationQA_Study")
    assert ("upload", "TC08") in calls
    assert ("validate",) in calls
    assert calls[-1] == ("verify", "TC08", "GC")


@pytest.mark.unit
def test_unknown_action_raises(tmp_path: Path) -> None:
    path = tmp_path / "TC99_unknown.xlsx"
    _write_minimal_excel_case(
        path,
        role="Submitter",
        input_root="InputFiles/CRDC/MetadataData/TC08",
        steps=[("not_a_real_action", "", "")],
    )

    class StubHub:
        page = object()
        locators = object()

    with pytest.raises(ExcelLoadError, match="Unknown step action"):
        run_testcase_excel(StubHub(), path)  # type: ignore[arg-type]


@pytest.mark.unit
def test_excel_ds_enabled_from_example_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CRDC_EXCEL_DS_VALIDATION", raising=False)
    _, example = profile_paths(repo_root(), "qa")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    shutil.copy(example, cfg_dir / "qa.yaml.example")
    settings = load_settings(profile="qa", root=tmp_path)
    assert excel_ds_enabled(settings) is True
    assert "DataValidation" in excel_ds_cases_glob(settings)


@pytest.mark.unit
def test_excel_ds_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        profile="qa",
        base_url="https://example/",
        config_path=Path("/tmp/qa.yaml"),
        data={},
    )
    monkeypatch.setenv("CRDC_EXCEL_DS_VALIDATION", "1")
    assert excel_ds_enabled(settings) is True
