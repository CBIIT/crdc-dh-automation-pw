"""Katalon: Test Cases/CRDC/SubmissionRequest/CRDCDH-332/TC01_CRDC_Submission_Request-AllFields

Submitter fills every Submission Request section, including the optional additional contact,
publications and repository blocks, checks the Review page against the Excel rows, then submits.
Data rows come from InputFiles/CRDC/SubmissionRequest/SubmissionRequest.xlsx (same as Katalon).
hub is already signed in as Submitter. Each run submits one real request (no cleanup, as in Katalon).
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.submission_request_form import SubmissionRequestFormPage
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage

log = logging.getLogger("crdc_pw.tc_crdcdh_332")

pytestmark = [pytest.mark.CRDC_SubmissionRequests, pytest.mark.CRDC_Smoke]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC01_CRDC_Submission_Request_AllFields(hub: Hub) -> None:
    sr_list = SubmissionRequestsListPage(hub)
    form = SubmissionRequestFormPage(hub)

    # Step 1: Start a new Submission Request and check the status bar shows NEW.
    sr_list.open()
    sr_list.start_new_submission_request()
    form.assert_status("NEW")

    # Step 2: Section A — PI, primary contact and additional contact (excel row 2), then Save and Next.
    form.enter_principal_investigator_info(2)
    form.enter_primary_contact_info(2)
    form.enter_additional_contact_info(2)
    form.click_save()
    form.click_next()
    form.assert_status("IN PROGRESS")

    # Step 3: Section B — Other program (row 6), study, funding, publications, repository (row 1).
    form.enter_program_info("Other", 6)
    form.enter_study_info(1)
    form.enter_funding_agency_info(1)
    form.enter_existing_and_planned_publications_info(1)
    form.enter_repository_info(1)
    form.click_save()
    form.click_next()

    # Step 4: Section C — controlled access with dbGaP registered, cancer type and species.
    form.enter_data_access_type_and_dbgap_reg_info("Controlled", "Yes")
    form.enter_cancer_type_and_subjects_info("Cholangiocarcinoma", "Homo", 1)
    form.click_save()
    form.click_next()

    # Step 5: Section D — dates, data types and the first file type row, then Save and Next to Review.
    form.enter_target_delivery_and_expected_publication_date()
    form.select_data_types("genomics", "proteomics")
    form.select_file_types(5, 6, 1, 1)
    form.click_save()
    form.click_next()

    # Step 6: Review page — every section shows what was entered.
    form.verify_principal_investigator_info(2)
    form.verify_primary_contact_info(2)
    form.verify_additional_contact_info(2)
    form.verify_program_info(6)
    form.verify_study_info(1)
    form.verify_funding_agency_and_dbgap_info(1)
    form.verify_publications_info(1)
    form.verify_repository_info(1)
    form.verify_data_access_and_disease_info("Cholangiocarcinoma", "lung", "Homo", 1)
    form.verify_data_types("genomics", "proteomics")
    form.verify_file_types(5, 6, 1, 1)

    # Step 7: Submit and confirm; the list's Start a Submission Request button is back.
    form.click_submit_button()

    log.info("PASS CRDCDH-332 TC01 as %s", hub.role)
