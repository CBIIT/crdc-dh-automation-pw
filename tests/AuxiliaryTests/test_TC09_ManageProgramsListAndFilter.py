"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC09_ManageProgramsListAndFilter

`app` is already signed in as Admin.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.app import App

log = logging.getLogger("crdc_pw.tc09")


@pytest.mark.smoke
def test_TC09_ManageProgramsListAndFilter(app: App) -> None:
    app.programs.navigate_to_manage_programs()

    app.programs.verify_list_page()

    app.programs.apply_filters(program_name="AutoTest", study_name="autoQA")

    app.programs.verify_filter_results(expect_at_least_rows=1, row_contains="auto")

    log.info("PASS TC09: Manage Programs list filtered to AutoTest/autoQA as %s", app.role)
