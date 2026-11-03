"""Katalon: Test Cases/CRDC/SubmissionRequest/CRDCDH-3948/TC02_CRDCDH-3948_InProgress_SaveRequiresNewContent

Xray CRDCDH-3948 TC02 — In Progress SRF: Save requires new content.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.submission_request import SubmissionRequest
from crdc_pw.pages.submission_request_form import (
    SR_IMPORT_VALIDATION_ERRORS_FIXTURE,
    SR_IMPORT_VALIDATION_ERRORS_MESSAGE,
    SubmissionRequestFormPage,
)
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage

log = logging.getLogger("crdc_pw.tc_crdcdh_3948")

pytestmark = pytest.mark.CRDC_SubmissionRequests


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC02_CRDCDH_3948_InProgress_SaveRequiresNewContent(hub: Hub) -> None:
    hub.page.set_viewport_size({"width": 1920, "height": 1080})

    sr_list = SubmissionRequestsListPage(hub)
    form = SubmissionRequestFormPage(hub)
    sr = SubmissionRequest(hub)

    # Setup: partial Sections A + B, save, reopen from list
    sr_list.open()
    sr_list.start_new_submission_request()
    sr.enter_principal_investigator_info(2)
    sr.enter_primary_contact_info(2)
    form.click_save()
    form.click_next()
    sr.enter_program_info("Other", 6)
    sr.enter_study_info(1)
    sr.enter_funding_agency_info(1)
    hub.page.wait_for_timeout(2000)
    form.click_save()
    form.assert_status("IN PROGRESS")

    study_name = SubmissionRequest.last_entered_study_title
    assert study_name
    sr.open_submission_request_form_for_study(study_name)
    form.assert_status("IN PROGRESS")

    # Step 2: no new edits — Save disabled + tooltip
    form.assert_save_disabled()
    form.assert_save_disabled_tooltip()

    # Step 3: import validation-errors fixture
    import_path = repo_root() / SR_IMPORT_VALIDATION_ERRORS_FIXTURE
    form.import_form_excel(import_path)
    form.assert_snackbar_contains(SR_IMPORT_VALIDATION_ERRORS_MESSAGE)
    form.assert_save_disabled()

    # Step 4: edit PI address — Save enabled
    form.set_pi_address("2 Automation Test Address")
    form.assert_save_enabled()

    log.info("PASS CRDCDH-3948 TC02 as %s", hub.role)
