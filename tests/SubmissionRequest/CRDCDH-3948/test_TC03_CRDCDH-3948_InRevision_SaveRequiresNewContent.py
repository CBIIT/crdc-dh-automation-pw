"""Katalon: Test Cases/CRDC/SubmissionRequest/CRDCDH-3948/TC03_CRDCDH-3948_InRevision_SaveRequiresNewContent

CRDCDH-3948 TC03 — Submission Request status: In Revision (after Fed Lead Inquire).
Submitter submit → Fed Lead inquire → Submitter reopens form; Save rules; save keeps IN REVISION.
Fixture starts signed in as Submitter; page objects are Hub-backed (survive switch_user).
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.auth import switch_user
from crdc_pw.hub import Hub
from crdc_pw.pages.submission_request_form import (
    SR_IMPORT_NO_CHANGES_MESSAGE,
    SubmissionRequestFormPage,
)
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage

log = logging.getLogger("crdc_pw.tc_crdcdh_3948")

pytestmark = pytest.mark.CRDC_SubmissionRequests


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC03_CRDCDH_3948_InRevision_SaveRequiresNewContent(hub: Hub) -> None:
    hub.page.set_viewport_size({"width": 1920, "height": 1080})

    sr_list = SubmissionRequestsListPage(hub)
    form = SubmissionRequestFormPage(hub)

    # --- Submitter: full questionnaire and submit ---
    sr_list.open()
    sr_list.start_new_submission_request()
    form.fill_submission_request_all_sections(
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
    study_name = SubmissionRequestFormPage.last_entered_study_title
    assert study_name
    form.click_submit_button()

    # Step 1: Fed Lead inquires on that study — SR moves to In Revision.
    switch_user(hub, "Fedlead")
    form.inquire_submission_request(study_name)

    # Step 2: Submitter reopens form from list — verify status bar IN REVISION.
    switch_user(hub, "Submitter")
    form.open_submission_request_form_for_study(study_name)
    form.assert_status("IN REVISION")

    # Step 3: No new edits — Save disabled and tooltip.
    form.assert_save_disabled()
    form.assert_save_disabled_tooltip()

    # Step 4: Export and re-import unchanged Excel — no-change snackbar (3948 req 3); Save still disabled.
    exported = form.export_form_excel()
    form.import_form_excel(exported)
    form.assert_snackbar_contains(SR_IMPORT_NO_CHANGES_MESSAGE)
    form.assert_save_disabled()

    # Step 5: Edit PI Address — verify Save enabled.
    form.set_pi_address("3 Automation Test Address")
    form.assert_save_enabled()

    # Step 6: Save while In Revision — status remains IN REVISION (does not revert to In Progress).
    form.click_save()
    form.assert_status("IN REVISION")

    log.info("PASS CRDCDH-3948 TC03 as %s", hub.role)
