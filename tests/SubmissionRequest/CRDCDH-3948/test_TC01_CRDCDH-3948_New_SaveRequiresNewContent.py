"""Katalon: Test Cases/CRDC/SubmissionRequest/CRDCDH-3948/TC01_CRDCDH-3948_New_SaveRequiresNewContent

CRDCDH-3948 TC01 — Submission Request status: New.
Submitter: Save stays disabled until the form is dirty; unchanged import; save moves status to In Progress.
Parent: CRDCDH-3880. hub is already signed in as Submitter.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.submission_request_form import (
    SR_IMPORT_NO_CHANGES_MESSAGE,
    SubmissionRequestFormPage,
)
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage

log = logging.getLogger("crdc_pw.tc_crdcdh_3948")

pytestmark = pytest.mark.CRDC_SubmissionRequests


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC01_CRDCDH_3948_New_SaveRequiresNewContent(hub: Hub) -> None:
    hub.page.set_viewport_size({"width": 1920, "height": 1080})

    sr_list = SubmissionRequestsListPage(hub)
    form = SubmissionRequestFormPage(hub)

    # Step 1: Start a new Submission Request — verify status bar shows NEW.
    sr_list.open()
    sr_list.start_new_submission_request()
    form.assert_status("NEW")

    # Step 2: With no unsaved edits — Save disabled and hover tooltip explains why.
    form.assert_save_disabled()
    form.assert_save_disabled_tooltip()

    # Step 3: Export form to Excel, re-import the same file — no-change snackbar (3948 req 3);
    #         Save remains disabled because nothing new was applied.
    exported = form.export_form_excel()
    form.import_form_excel(exported)
    form.assert_snackbar_contains(SR_IMPORT_NO_CHANGES_MESSAGE)
    form.assert_save_disabled()

    # Step 4: Change PI Address — verify Save becomes enabled.
    form.set_pi_address("1 Automation Test Address")
    form.assert_save_enabled()

    # Step 5: Click Save — verify status bar changes from NEW to IN PROGRESS.
    form.click_save()
    form.assert_status("IN PROGRESS")

    log.info("PASS CRDCDH-3948 TC01 as %s", hub.role)
