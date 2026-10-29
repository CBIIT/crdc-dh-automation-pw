"""Pytest plugin: collect tests/DataValidation/**/TC*.xlsx when excel_ds_validation is enabled."""

from __future__ import annotations

from pathlib import Path

import pytest

from crdc_pw.config import load_settings
from crdc_pw.locators.loader import repo_root
from crdc_pw.utils.excel_ds_test_runner.config_helpers import excel_ds_enabled
from crdc_pw.utils.excel_ds_test_runner.loader import read_meta, read_meta_role
from crdc_pw.utils.excel_ds_test_runner.step_runner import run_testcase_excel


def _is_excel_case_path(path: Path) -> bool:
    if path.suffix.lower() != ".xlsx" or path.name.startswith("~$"):
        return False
    if not path.name.startswith("TC"):
        return False
    if path.name.startswith("TC_Template"):
        return False
    try:
        rel = path.resolve().relative_to(repo_root().resolve())
    except ValueError:
        return False
    parts = rel.parts
    return len(parts) >= 3 and parts[0] == "tests" and parts[1] == "DataValidation"


def _make_test_fn(case_path: Path, role: str):
    @pytest.mark.parametrize("hub", [role], indirect=True)
    @pytest.mark.CRDC_DataValidation
    @pytest.mark.CRDC_DataValidation_Excel
    def test_fn(hub):
        run_testcase_excel(hub, case_path)

    test_fn.__name__ = case_path.stem
    return test_fn


class ExcelCaseFile(pytest.File):
    """One TC*.xlsx → one pytest test."""

    def collect(self):
        case_path = Path(str(self.path))
        meta = read_meta(case_path)
        if meta.get("enabled", "y").strip().lower() in ("n", "no", "false", "0"):
            return
        role = read_meta_role(case_path)
        fn = _make_test_fn(case_path, role)
        yield pytest.Function.from_parent(self, name=case_path.stem, callobj=fn)


def pytest_collect_file(file_path, parent):
    if not excel_ds_enabled(load_settings()):
        return None
    path = Path(str(file_path))
    if not _is_excel_case_path(path):
        return None
    return ExcelCaseFile.from_parent(parent, path=path)
