"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-1163/TC16_CRDC-1163-DCPValidationAfterSubmissionSubmittedMetadata

`hub` starts signed in as Submitter; Dcp is reached with switch_user.
No ValidationReport (Katalon generateValidationReport omitted in Playwright port).

Flow:
  1. Submitter creates a New GC metadata-only submission (ATS study), uploads a unique
     program.tsv, validates and submits it
  2. Dcp opens that submission by id: status is Submitted, Validate is still enabled,
     Validation Type is Metadata, Validation Target is All Uploaded Data, and
     New Uploaded Data is not selected
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.data_submission_details import DataSubmissionDetailPage
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.utils.pbac_helpers import AUTOMATION_STUDY_DS, prepare_unique_program_tsv
from crdc_pw.utils.ui_helpers import (
    assert_button_enabled,
    assert_button_selected,
    assert_element_text,
)

log = logging.getLogger("crdc_pw.tc1163_16")

pytestmark = [pytest.mark.CRDC_Smoke, pytest.mark.CRDC_DSFlow]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC16_CRDCDH_1163_DCPValidationAfterSubmissionSubmittedMetadata(hub: Hub) -> None:
    ds_list = DataSubmissionsListPage(hub)
    detail = DataSubmissionDetailPage(hub)

    # 1. Submitter: create, upload a unique program.tsv, validate, submit
    ds_list.open()
    submission_name = ds_list.create_data_submission(
        "New/Update", "metadata only", "GC", AUTOMATION_STUDY_DS
    )
    log.info("Created submission %s", submission_name)
    detail.wait_loading_spinner_gone()
    temp = prepare_unique_program_tsv()
    try:
        detail.upload_metadata_file(temp)
    finally:
        temp.unlink(missing_ok=True)
    detail.click_validate()
    detail.click_submit_for_review()
    detail.wait_loading_spinner_gone()
    submission_id = detail.submission_id_from_url()

    # 2. Dcp: open the submission by id
    switch_user(hub, "Dcp")
    detail.open_upload_activity(submission_id)

    # After the submission is submitted, status is Submitted
    assert_element_text(detail.status_label, "Submitted")
    log.info("Assert status is Submitted")
    # Validate is still enabled for the Dcp
    assert_button_enabled(detail.validate_button, True)
    # A metadata-only submission defaults to Validation Type Metadata
    assert_button_selected(detail.validation_type_metadata_radio, True)
    # Validation Target is All Uploaded Data; New Uploaded Data is not selected
    assert_button_selected(detail.validation_target_all_radio, True)
    assert_button_selected(detail.validation_target_new_radio, False)
    log.info("Assert Dcp validation controls for a Submitted metadata-only submission")
