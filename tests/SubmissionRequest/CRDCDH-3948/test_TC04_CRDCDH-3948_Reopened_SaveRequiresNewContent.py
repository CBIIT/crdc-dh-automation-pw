"""Katalon: Test Cases/CRDC/SubmissionRequest/CRDCDH-3948/TC04_CRDCDH-3948_Reopened_SaveRequiresNewContent

CRDCDH-3948 TC04 — Submission Request status: Reopened (Fed Lead Approve + Reopen on list).
Same Save/import checks as TC01–TC03; save after edit transitions Reopened → In Progress.
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
def test_TC04_CRDCDH_3948_Reopened_SaveRequiresNewContent(hub: Hub) -> None:
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

    # Step 1: Fed Lead approves, then Reopen from list (does not open the questionnaire).
    switch_user(hub, "Fedlead")
    form.approve_submission_request(study_name)
    form.reopen_approved_submission_request(study_name)

    # Step 2: Submitter opens form from list — verify status bar REOPENED.
    switch_user(hub, "Submitter")
    form.open_submission_request_form_for_study(study_name)
    form.assert_status("REOPENED")

    # Step 3: No new edits — Save disabled and tooltip.
    form.assert_save_disabled()
    form.assert_save_disabled_tooltip()

    # Step 4: Export and re-import unchanged Excel — no-change snackbar (3948 req 3); Save still disabled.
    exported = form.export_form_excel()
    form.import_form_excel(exported)
    form.assert_snackbar_contains(SR_IMPORT_NO_CHANGES_MESSAGE)
    form.assert_save_disabled()

    # Step 5: Edit editable field on Reopened form (Primary Contact position; PI address is read-only) — Save enabled.
    form.click_progress_bar_section_a()
    form.set_primary_contact_position("3948 Reopened Position")
    form.assert_save_enabled()

    # Step 6: Save — verify status transitions from REOPENED to IN PROGRESS.
    form.click_save()
    form.assert_status("IN PROGRESS")

    log.info("PASS CRDCDH-3948 TC04 as %s", hub.role)
