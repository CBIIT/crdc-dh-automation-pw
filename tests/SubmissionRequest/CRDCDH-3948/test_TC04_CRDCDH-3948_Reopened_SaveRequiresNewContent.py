"""Katalon: Test Cases/CRDC/SubmissionRequest/CRDCDH-3948/TC04_CRDCDH-3948_Reopened_SaveRequiresNewContent

Xray CRDCDH-3948 TC04 — Reopened SRF: Save requires new content.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.submission_request import SubmissionRequest
from crdc_pw.pages.submission_request_form import (
    SR_IMPORT_NO_CHANGES_MESSAGE,
    SubmissionRequestFormPage,
)
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage

log = logging.getLogger("crdc_pw.tc_crdcdh_3948")

pytestmark = pytest.mark.CRDC_SubmissionRequests


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC04_CRDCDH_3948_Reopened_SaveRequiresNewContent(hub: Hub) -> None:
    hub.page.set_viewport_size({"width": 1920, "height": 1080})

    sr_list = SubmissionRequestsListPage(hub.page, hub.locators)
    form = SubmissionRequestFormPage(hub.page, hub.locators)
    sr = SubmissionRequest(hub.page, hub.locators)

    sr_list.open()
    sr_list.start_new_submission_request()
    sr.fill_submission_request_all_sections(
        2,
        "Other",
        6,
        1,
        1,
        "Open",
        "Yes",
        "Cholangiocarcinoma",
        "Homo",
        1,
        "genomics",
        "proteomics",
        5,
        6,
        1,
        1,
    )
    study_name = SubmissionRequest.last_entered_study_title
    assert study_name
    form.click_submit_button()

    switch_user(hub, "Fedlead")
    sr = SubmissionRequest(hub.page, hub.locators)
    form = SubmissionRequestFormPage(hub.page, hub.locators)
    sr.approve_submission_request(study_name)
    sr.reopen_approved_submission_request(study_name)

    switch_user(hub, "Submitter")
    sr = SubmissionRequest(hub.page, hub.locators)
    form = SubmissionRequestFormPage(hub.page, hub.locators)
    sr.open_submission_request_form_for_study(study_name)
    form.assert_status("REOPENED")

    form.assert_save_disabled()
    form.assert_save_disabled_tooltip()

    exported = form.export_form_excel()
    form.import_form_excel(exported)
    form.assert_snackbar_contains(SR_IMPORT_NO_CHANGES_MESSAGE)
    form.assert_save_disabled()

    form.click_progress_bar_section_a()
    form.set_primary_contact_position("3948 Reopened Position")
    form.assert_save_enabled()

    form.click_save()
    form.assert_status("IN PROGRESS")

    log.info("PASS CRDCDH-3948 TC04 as %s", hub.role)
