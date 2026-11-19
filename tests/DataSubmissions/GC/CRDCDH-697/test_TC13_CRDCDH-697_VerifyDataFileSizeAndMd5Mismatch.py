"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-697/TC13_CRDC-VerifyDataFileSizeAndMd5Mismatch

`hub` starts signed in as Submitter.
No ValidationReport (Katalon generateValidationReport omitted in Playwright port).

Needs SubmitterApiToken in config/<profile>.yaml (the test fails with a clear message when it is
empty) and Python 3.13 or newer for the CLI.

Flow:
  1. Submitter creates a New GC "both" (metadata and data files) submission and reads its id
  2. Upload the data files with the CLI. The manifest has a wrong file size (demo1.xlsx), a wrong md5
     (demo2.pdf) and a file that is not in the folder, so the CLI finds invalid files
  3. The CLI's upload report has, for each file, the errors in CRDCDH-697_TC13/expected/*.tsv

Differences from Katalon: it only logged a warning when the CLI output lacked the success lines, and it
did not say so; here the upload is told to expect validation errors, and step 3 is the check.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submission_details import DS_AUTOMATION_STUDY_CREATE, DataSubmissionDetailPage
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.utils.cli_verifications import verify_cli_error_messages
from crdc_pw.pages.cli_uploader import require_submitter_token, upload_files_via_cli

log = logging.getLogger("crdc_pw.tc697_13")

TC_NAME = "CRDCDH-697_TC13"

pytestmark = [pytest.mark.CRDC_DataFileUpload, pytest.mark.CRDC_Regression]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC13_CRDCDH_697_VerifyDataFileSizeAndMd5Mismatch(hub: Hub, tmp_path: Path) -> None:
    require_submitter_token(hub.settings)  # fail before a submission is created
    ds_list = DataSubmissionsListPage(hub)
    detail = DataSubmissionDetailPage(hub)

    # 1. Submitter: create the submission and read its id from the URL
    ds_list.open()
    submission_name = ds_list.create_data_submission("New", "both", "GC", DS_AUTOMATION_STUDY_CREATE)
    submission_id = detail.submission_id_from_url()
    log.info("Created submission %s (%s)", submission_name, submission_id)

    # 2. CLI upload of the data files; the CLI is expected to reject some of them
    upload = upload_files_via_cli(
        hub.settings, submission_id, TC_NAME, "datafile", tmp_path, expect_validation_errors=True
    )

    # 3. Upload report errors per file vs expected
    verify_cli_error_messages(upload, TC_NAME)
