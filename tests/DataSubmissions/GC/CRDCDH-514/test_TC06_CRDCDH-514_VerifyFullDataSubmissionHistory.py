"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-514/TC06_CRDC-514-VerifyFullDataSubmissionHistory

`hub` starts signed in as Submitter; Dcp is reached with switch_user.
No ValidationReport (Katalon generateValidationReport omitted in Playwright port).

Flow:
  1. Submitter creates a New GC metadata-only submission (ATS study), uploads a unique
     program.tsv, validates (In Progress) and submits
  2. Dcp opens it by id (Submitted) and rejects it with a justification
  3. Submitter opens it (Rejected), validates again, refreshes and submits
  4. Dcp opens it (Submitted), cross-validates, Releases (Released) and Completes (Completed)
  5. Full History lists, newest first:
     COMPLETED, RELEASED, SUBMITTED, REJECTED, SUBMITTED, INPROGRESS, NEW
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.data_submission_details import DataSubmissionDetailPage
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.utils.pbac_helpers import AUTOMATION_STUDY_DS, prepare_unique_program_tsv
from crdc_pw.utils.ui_helpers import assert_element_text, diff_history_statuses

log = logging.getLogger("crdc_pw.tc514_06")

# Newest first, as the Full History dialog lists them.
EXPECTED_HISTORY_NEWEST_FIRST = [
    "COMPLETED",
    "RELEASED",
    "SUBMITTED",
    "REJECTED",
    "SUBMITTED",
    "INPROGRESS",
    "NEW",
]

pytestmark = [pytest.mark.CRDC_Smoke, pytest.mark.CRDC_DSFlow]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC06_CRDCDH_514_VerifyFullDataSubmissionHistory(hub: Hub) -> None:
    ds_list = DataSubmissionsListPage(hub)
    detail = DataSubmissionDetailPage(hub)

    # 1. Submitter: create, upload a unique program.tsv, validate, submit
    ds_list.open()
    submission_name = ds_list.create_data_submission(
        "New/Update", "metadata only", "GC", AUTOMATION_STUDY_DS
    )
    log.info("Created submission %s", submission_name)
    detail.wait_loading_spinner_gone()
    assert_element_text(detail.status_label, "New")
    temp = prepare_unique_program_tsv()
    try:
        detail.upload_metadata_file(temp)
    finally:
        temp.unlink(missing_ok=True)
    detail.click_validate()
    assert_element_text(detail.status_label, "In Progress")
    detail.click_submit_for_review()
    detail.wait_loading_spinner_gone()
    submission_id = detail.submission_id_from_url()

    # 2. Dcp: status Submitted, then reject with a justification
    switch_user(hub, "Dcp")
    detail.open_upload_activity(submission_id)
    assert_element_text(detail.status_label, "Submitted")
    detail.reject_button.first.click()
    detail.reject_comment.first.fill("Rejecting")
    detail.confirm_reject_button.first.click()

    # 3. Submitter: status Rejected, validate again, refresh, submit again
    switch_user(hub, "Submitter")
    detail.open_upload_activity(submission_id)
    assert_element_text(detail.status_label, "Rejected")
    detail.click_validate()

    detail.click_submit_for_review()

    # 4. Dcp: status Submitted, cross-validate, Release, Complete
    switch_user(hub, "Dcp")
    detail.open_upload_activity(submission_id)
    assert_element_text(detail.status_label, "Submitted")
    expect(detail.cross_validate_button.first).to_be_enabled(timeout=30_000)
    detail.cross_validate_button.first.click()
    # Katalon waits up to 5 minutes for cross-validation to finish (button enabled again)
    expect(detail.cross_validate_button.first).to_be_enabled(timeout=300_000)
    detail.click_release()
    detail.click_release_confirmation_yes()
    assert_element_text(detail.status_label, "Released")
    detail.complete_button.first.click()
    detail.complete_confirmation_yes.first.click()
    assert_element_text(detail.status_label, "Completed")

    # 5. Full History dialog lists every status change, newest first
    detail.full_history_button.first.click()
    expect(detail.history_dialog.first).to_be_visible(timeout=10_000)
    actual = detail.read_history_statuses()
    problem = diff_history_statuses(EXPECTED_HISTORY_NEWEST_FIRST, actual)
    detail.history_close_button.first.click()
    assert problem is None, problem
    log.info("Assert Full History (newest first): %s", ", ".join(actual))
