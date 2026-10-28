"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC08_ManageStudiesListAndFilter

`app` is already signed in as Admin.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.app import App

log = logging.getLogger("crdc_pw.tc08")


@pytest.mark.smoke
def test_TC08_ManageStudiesListAndFilter(app: App) -> None:
    app.studies.navigate_to_manage_studies()

    app.studies.verify_list_page()

    app.studies.apply_filters(study_name="autoQA", program="AutoTest-Program")

    app.studies.verify_filter_results(expect_at_least_rows=1, row_contains="autoQA")

    log.info("PASS TC08: Manage Studies list filtered to autoQA as %s", app.role)
