"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-1051/TC25_CRDC-VerifyDcpCrossValidation

`hub` starts signed in as Submitter; Dcp is reached with switch_user.
No ValidationReport (Katalon generateValidationReport omitted in Playwright port).

Flow:
  1. Submitter creates two GC metadata-only submissions in the same study
     (autoQA - AutomationQA_CV), uploads the same program.tsv into both (same
     program_acronym, the cross-validation key), validates and submits each
  2. Dcp opens submission 2, cross-validates, and the Cross Validation Results rows that
     link to submission 1 match the expected TSV (Conflict Data found)
  3. Dcp rejects submission 2, then submission 1 (status Rejected each time)

Expected rows: InputFiles/CRDC/MetadataData/CRDCDH-1051_TC25/expected-CrossValidationResults
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.data_submission_details import DS_AUTOMATION_STUDY_CV, DataSubmissionDetailPage
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.utils.ui_helpers import assert_element_text
from crdc_pw.utils.validation_results import diff_cross_validation_rows, load_expected_cross_validation_rows

log = logging.getLogger("crdc_pw.tc1051_25")

TC_NAME = "CRDCDH-1051_TC25"

pytestmark = [pytest.mark.CRDC_Smoke, pytest.mark.CRDC_DSFlow, pytest.mark.CRDC_DataValidation]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC25_CRDCDH_1051_VerifyDcpCrossValidation(hub: Hub) -> None:
    ds_list = DataSubmissionsListPage(hub)
    detail = DataSubmissionDetailPage(hub)

    # 1a. Submitter: submission 1 (create, upload program.tsv, validate, submit)
    ds_list.open()
    name_1 = ds_list.create_data_submission("New", "metadata only", "GC", DS_AUTOMATION_STUDY_CV)
    log.info("Created submission 1: %s", name_1)
    detail.upload_folder(TC_NAME)
    detail.click_validate()
    detail.click_submit_for_review()
    detail.wait_loading_spinner_gone()
    submission_id_1 = detail.submission_id_from_url()
    log.info("Submitter submitted submission 1: %s (%s)", name_1, submission_id_1)

    # 1b. Submitter: submission 2 in the same study with the same program.tsv
    ds_list.open()
    name_2 = ds_list.create_data_submission("New", "metadata only", "GC", DS_AUTOMATION_STUDY_CV)
    log.info("Created submission 2: %s", name_2)
    detail.upload_folder(TC_NAME)
    detail.click_validate()
    detail.click_submit_for_review()
    detail.wait_loading_spinner_gone()
    submission_id_2 = detail.submission_id_from_url()
    log.info("Submitter submitted submission 2: %s (%s)", name_2, submission_id_2)

    # 2. Dcp: cross-validate submission 2, then check the rows that point at submission 1
    switch_user(hub, "Dcp")
    detail.open_upload_activity(submission_id_2)
    log.info("Dcp opened submission 2 (%s); clicking Cross Validate", submission_id_2)
    expect(detail.cross_validate_button.first).to_be_enabled(timeout=30_000)
    detail.cross_validate_button.first.click()
    # Katalon waits up to 5 minutes for cross-validation to finish (button enabled again)
    expect(detail.cross_validate_button.first).to_be_enabled(timeout=300_000)
    log.info("Cross-validation finished for submission 2")
    expected = load_expected_cross_validation_rows(TC_NAME)
    actual = detail.read_cross_validation_rows_for_peer(submission_id_1)
    problems = diff_cross_validation_rows(expected, actual)
    assert not problems, "Cross Validation Results mismatch:\n" + "\n".join(problems)
    log.info("Assert Cross Validation Results match expected (%s rows)", len(actual))

    # 3a. Reject submission 2
    expect(detail.reject_button.first).to_be_visible()
    log.info("Dcp rejecting submission 2 (%s)", submission_id_2)
    detail.reject_button.first.click()
    detail.reject_comment.first.fill("testing Reject")
    detail.confirm_reject_button.first.click()
    assert_element_text(detail.status_label, "Rejected")
    log.info("Assert submission 2 status is Rejected")

    # 3b. Reject submission 1
    detail.open_upload_activity(submission_id_1)
    expect(detail.reject_button.first).to_be_visible()
    log.info("Dcp rejecting submission 1 (%s)", submission_id_1)
    detail.reject_button.first.click()
    detail.reject_comment.first.fill("testing Reject")
    detail.confirm_reject_button.first.click()
    assert_element_text(detail.status_label, "Rejected")
    log.info("Assert submission 1 status is Rejected")
