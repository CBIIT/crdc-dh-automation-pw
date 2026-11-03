"""Xray CRDCDH-3948 — New SRF: Save requires new content (TC01).

Parent story: CRDCDH-3880. Katalon:
Test Cases/CRDC/SubmissionRequest/CRDCDH-3948/TC01_CRDCDH-3948_New_SaveRequiresNewContent

hub is already signed in as Submitter.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.submission_request_form import SubmissionRequestFormPage
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage
from crdc_pw.submission_request.constants import SR_IMPORT_NO_CHANGES_MESSAGE

log = logging.getLogger("crdc_pw.tc_crdcdh_3948")

pytestmark = pytest.mark.CRDC_SubmissionRequests


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC_CRDCDH_3948_New_SaveRequiresNewContent(hub: Hub) -> None:
    hub.page.set_viewport_size({"width": 1920, "height": 1080})

    sr_list = SubmissionRequestsListPage(hub.page, hub.locators)
    form = SubmissionRequestFormPage(hub.page, hub.locators)

    # Step 1: new questionnaire — status NEW
    sr_list.open()
    sr_list.start_new_submission_request()
    form.assert_status("NEW")

    # Step 2: no edits — Save disabled + tooltip
    form.assert_save_disabled()
    form.assert_save_disabled_tooltip()

    # Step 3: export, re-import same file — no-change snackbar; Save still disabled
    exported = form.export_form_excel()
    form.import_form_excel(exported)
    form.assert_snackbar_contains(SR_IMPORT_NO_CHANGES_MESSAGE)
    form.assert_save_disabled()

    # Step 4–5: dirty PI address — Save enabled; Save → IN PROGRESS
    form.set_pi_address("1 Automation Test Address")
    form.assert_save_enabled()
    form.click_save()
    form.assert_status("IN PROGRESS")

    log.info("PASS CRDCDH-3948 TC01 as %s", hub.role)
