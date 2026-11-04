"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-697/TC01_CRDC-VerifyDataSubmissionHeaders

Submitter creates a GC metadata-only submission and verifies summary header fields and tooltips.
No ValidationReport (Katalon generateValidationReport omitted in Playwright port).

Flow:
  1. Data Submissions → create New GC metadata-only for autoQA study
  2. Read summary header on detail page
  3. Assert field values (name from create, QA automation constants for study/program/concierge)
  4. Hover tooltips on collaborators and submission name
"""

from __future__ import annotations

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submission_details import (
    DS_AUTOMATION_STUDY_CREATE,
    DS_COLLABORATORS_TOOLTIP,
    DS_EXPECTED_COLLABORATORS_COUNT,
    DS_EXPECTED_DATA_CONCIERGE,
    DS_EXPECTED_PROGRAM,
    DS_EXPECTED_STUDY_HEADER,
    DS_EXPECTED_SUBMISSION_TYPE_NEW,
    DataSubmissionDetailPage,
)
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.pages.header import HeaderPage
from crdc_pw.utils.ui_helpers import verify_tooltip_on_hover_page

pytestmark = [pytest.mark.CRDC_Smoke, pytest.mark.CRDC_DSFlow]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC01_CRDC_VerifyDataSubmissionHeaders(hub: Hub) -> None:
    ds_list = DataSubmissionsListPage(hub)

    # 1. Create a New GC metadata-only data submission
    ds_list.open()
    submission_name = ds_list.create_data_submission(
        "New", "metadata only", "GC", DS_AUTOMATION_STUDY_CREATE
    )

    detail = DataSubmissionDetailPage(hub)
    # 2. Read summary header fields
    actual = detail.read_summary_header()

    expected_submitter = f"{HeaderPage(hub).username().lower()} Please Do Not Edit"

    # 3. Assert header values (normalization in verify_summary_header_fields)
    detail.verify_summary_header_fields(
        {
            "submission_name": submission_name,
            "submitter": expected_submitter,
            "submission_type": DS_EXPECTED_SUBMISSION_TYPE_NEW,
            "collaborators": DS_EXPECTED_COLLABORATORS_COUNT,
            "study": DS_EXPECTED_STUDY_HEADER,
            "data_commons": "GC",
            "program": DS_EXPECTED_PROGRAM,
            "data_concierge": DS_EXPECTED_DATA_CONCIERGE,
        },
        actual=actual,
    )

    # 4. Tooltips (Katalon verifyDataSubmissionHeaders subset)
    verify_tooltip_on_hover_page(
        detail,
        detail.collaborators_button,
        DS_COLLABORATORS_TOOLTIP,
    )
    verify_tooltip_on_hover_page(
        detail,
        detail.submission_name_tooltip_trigger,
        submission_name,
    )
