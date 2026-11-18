"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-1035/TC101_CRDC-1035-VerifyValidationResultsExportAllRoles

`hub` starts signed in as Submitter; the other roles are reached with switch_user.
No ValidationReport (Katalon generateValidationReport omitted in Playwright port).

Flow:
  1. Submitter creates a New GC metadata-only submission, uploads TC04 and validates
  2. Validation Results tab: Export is enabled and the downloaded file name is
     {submission name}-YYYY-MM-DDThhmmss.csv|xlsx
  3. Dcp, Fedlead and Admin each open that submission by id and see Export enabled
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.data_submission_details import (
    DS_AUTOMATION_STUDY_CREATE,
    DataSubmissionDetailPage,
)
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage

log = logging.getLogger("crdc_pw.tc1035_101")

TC_NAME = "TC04"

pytestmark = [pytest.mark.CRDC_Smoke, pytest.mark.CRDC_DSFlow]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC101_CRDCDH_1035_VerifyValidationResultsExportAllRoles(hub: Hub) -> None:
    ds_list = DataSubmissionsListPage(hub)
    detail = DataSubmissionDetailPage(hub)

    # 1. Submitter: create, upload, validate
    ds_list.open()
    submission_name = ds_list.create_data_submission(
        "New", "metadata only", "GC", DS_AUTOMATION_STUDY_CREATE
    )
    log.info("Created submission %s", submission_name)
    detail.upload_folder(TC_NAME)
    detail.click_validate()

    # 2. Submitter: Export enabled, then download and check the file name
    detail.verify_validation_results_export_enabled()
    detail.export_validation_results_and_verify_filename(submission_name)
    submission_id = detail.submission_id_from_url()

    # 3. Other roles open the same submission by id and see Export enabled
    for role in ("Dcp", "Fedlead", "Admin"):
        switch_user(hub, role)
        detail.open_upload_activity(submission_id)
        detail.verify_validation_results_export_enabled()
        log.info("Assert Validation Results export enabled for %s", role)
