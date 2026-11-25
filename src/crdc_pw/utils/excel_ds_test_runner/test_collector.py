"""Pytest plugin: collect tests/DataValidation/**/TC*.xlsx and TC*.tsv when excel_ds_validation is enabled."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from _pytest.python import Function, FunctionDefinition, Metafunc

from crdc_pw.config import load_settings
from crdc_pw.locators.loader import repo_root
from crdc_pw.utils.excel_ds_test_runner.config_helpers import excel_ds_enabled
from crdc_pw.utils.excel_ds_test_runner.loader import read_settings, read_settings_role
from crdc_pw.utils.excel_ds_test_runner.step_runner import run_testcase_excel


CASE_SUFFIXES = (".xlsx", ".tsv")


def _is_excel_case_path(path: Path) -> bool:
    if path.suffix.lower() not in CASE_SUFFIXES or path.name.startswith("~$"):
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


# Workbooks that are members of the Katalon CRDC_Smoke suite (see crdc-dh-automation
# Test Suites/CRDC_Smoke.ts): 686-Partial TC03, 699 CTDC TC101, 699 ICDC TC36.
# These get the CRDC_Smoke marker in addition to the Excel markers. Keep names in sync with
# the workbook file names (a unit test checks each one exists).
_SMOKE_CASE_STEMS = frozenset(
    {
        "TC03_CRDCDH-686_VerifyInvalidStrPtrn-IncompibleConsCode",
        "TC101_CRDCDH-699_VerifyValidationResultsLongFormErrorsCTDC",
        "TC36_CRDCDH-699_RequiredRelatedPropertyMissingICDC",
    }
)


def _duplicate_format_error(case_path: Path) -> str | None:
    """Message when the same case stem exists as both .xlsx and .tsv in one folder."""
    siblings = [
        case_path.with_suffix(suffix)
        for suffix in CASE_SUFFIXES
        if case_path.with_suffix(suffix).is_file()
    ]
    if len(siblings) > 1:
        names = ", ".join(p.name for p in siblings)
        return f"Case {case_path.stem} exists in more than one format ({names}); keep only one"
    return None


def _make_test_fn(case_path: Path, role: str):
    @pytest.mark.parametrize("hub", [role], indirect=True)
    @pytest.mark.CRDC_DataValidation
    @pytest.mark.CRDC_DataValidation_Excel
    def test_fn(hub):
        run_testcase_excel(hub, case_path)

    if case_path.stem in _SMOKE_CASE_STEMS:
        test_fn = pytest.mark.CRDC_Smoke(test_fn)
    test_fn.__name__ = case_path.stem
    return test_fn


def _yield_parametrized_functions(
    parent: pytest.Collector, name: str, callobj: object
) -> Iterator[Function]:
    """Apply @pytest.mark.parametrize on callobj (PyCollector._genfunctions parity)."""
    definition = FunctionDefinition.from_parent(parent, name=name, callobj=callobj)
    fixtureinfo = definition._fixtureinfo
    metafunc = Metafunc(
        definition=definition,
        fixtureinfo=fixtureinfo,
        config=parent.config,
        module=None,
        _ispytest=True,
    )
    for marker in definition.iter_markers(name="parametrize"):
        metafunc.parametrize(*marker.args, **marker.kwargs, _param_mark=marker)

    if not metafunc._calls:
        yield Function.from_parent(
            parent, name=name, callobj=callobj, fixtureinfo=fixtureinfo
        )
        return

    metafunc._recompute_direct_params_indices()
    fixtureinfo.prune_dependency_tree()
    for callspec in metafunc._calls:
        subname = f"{name}[{callspec.id}]" if callspec._idlist else name
        keywords = {callspec.id: True} if callspec._idlist else {}
        yield Function.from_parent(
            parent,
            name=subname,
            callobj=callobj,
            callspec=callspec,
            fixtureinfo=fixtureinfo,
            keywords=keywords,
            originalname=name,
        )


class ExcelCaseFile(pytest.File):
    """One TC*.xlsx or TC*.tsv gives one pytest test."""

    def collect(self):
        case_path = Path(str(self.path))
        duplicate = _duplicate_format_error(case_path)
        if duplicate:
            raise pytest.UsageError(duplicate)
        settings = read_settings(case_path)
        if settings.get("enabled", "y").strip().lower() in ("n", "no", "false", "0"):
            return
        role = read_settings_role(case_path)
        fn = _make_test_fn(case_path, role)
        yield from _yield_parametrized_functions(self, case_path.stem, fn)


def pytest_collect_file(file_path, parent):
    if not excel_ds_enabled(load_settings()):
        return None
    path = Path(str(file_path))
    if not _is_excel_case_path(path):
        return None
    return ExcelCaseFile.from_parent(parent, path=path)
