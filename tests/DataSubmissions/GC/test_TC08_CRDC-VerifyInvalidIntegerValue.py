"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-686-Partial/TC08_CRDC-VerifyInvalidIntegerValue

hub is already signed in as Submitter. This file is the script after login.
Invalid integer values in GC diagnosis metadata; Validation Results vs expected TSV.

Flow:
  1. Create a New GC metadata-only data submission
  2. Upload InputFiles/CRDC/MetadataData/TC08/*.tsv
  3. Validate
  4. Compare Validation Results to expected-ValidationResults
"""

from __future__ import annotations

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submissions import DataSubmissionDetailPage, DataSubmissionsListPage

pytestmark = pytest.mark.CRDC_DataValidation


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC08_CRDC_VerifyInvalidIntegerValue(hub: Hub) -> None:
    ds = DataSubmissionsListPage(hub.page, hub.locators)

    # 1. Create a New GC metadata-only data submission
    ds.open()
    ds.create_data_submission("New", "metadata only", "GC", "autoQA - AutomationQA_Study")

    detail = DataSubmissionDetailPage(hub.page, hub.locators)
    # 2. Upload InputFiles/CRDC/MetadataData/TC08/*.tsv
    detail.upload_folder("TC08")
    # 3. Validate
    detail.click_validate()
    # 4. Compare Validation Results to expected-ValidationResults
    detail.verify_validation_results_vs_expected_for_tc("TC08", model="GC")
