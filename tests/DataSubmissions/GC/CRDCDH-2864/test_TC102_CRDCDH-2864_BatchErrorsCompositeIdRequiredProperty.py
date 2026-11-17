"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-2864/TC102_CRDC-2864-BatchErrorsCompositeIdRequiredProperty

`hub` is already signed in as Submitter (fixture). This file is the scenario after login.
No ValidationReport (Katalon generateValidationReport omitted in Playwright port).

Flow:
  1. Create a New GC metadata-only submission for the autoQA study (opens its Upload Activities page)
  2. Upload the invalid metadata TSVs in InputFiles/CRDC/MetadataData/CRDCDH-2864_TC102
  3. Upload Activities shows a Metadata batch of 4 files with status Failed
  4. The Upload Errors modal shows exactly the errors in CRDCDH-2864_TC102/expected/*.tsv
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submission_details import (
    DS_AUTOMATION_STUDY_CREATE,
    DataSubmissionDetailPage,
)
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage

log = logging.getLogger("crdc_pw.tc2864_102")

TC_NAME = "CRDCDH-2864_TC102"

pytestmark = [
    pytest.mark.CRDC_Smoke,
    pytest.mark.CRDC_DataValidation,
    pytest.mark.CRDC_Regression,
]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC102_CRDCDH_2864_BatchErrorsCompositeIdRequiredProperty(hub: Hub) -> None:
    ds_list = DataSubmissionsListPage(hub)
    detail = DataSubmissionDetailPage(hub)

    # 1. Create a New GC metadata-only data submission
    ds_list.open()
    submission_name = ds_list.create_data_submission(
        "New", "metadata only", "GC", DS_AUTOMATION_STUDY_CREATE
    )
    log.info("Created submission %s", submission_name)

    # 2. Upload the invalid metadata folder
    detail.upload_folder(TC_NAME)

    # 3. Upload Activities: Metadata batch, 4 files, Failed
    detail.verify_upload_activities_batch_row("Metadata", 4, "Failed")
    log.info("Assert Upload Activities: Metadata batch, 4 files, Failed")

    # 4. Upload Errors modal vs expected TSVs
    detail.verify_upload_errors_modal(TC_NAME)
    log.info("Assert Upload Errors modal matches expected errors for %s", TC_NAME)
