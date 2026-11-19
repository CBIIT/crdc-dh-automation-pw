"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-1405/TC101_CRDC-1405-CLINoFileIdVerifyFinalManifest

`hub` starts signed in as Submitter.
No ValidationReport (Katalon generateValidationReport omitted in Playwright port).

Needs SubmitterApiToken in config/<profile>.yaml (the test fails with a clear message when it is
empty) and Python 3.13 or newer for the CLI. The CLI's requirements are installed before each run, as
Katalon does.

Flow:
  1. Submitter creates a New GC "both" (metadata and data files) submission and reads its id
  2. Upload the data files with the CLI, using a manifest that has no file_id column
  3. The CLI wrote <manifest>-final.tsv: it has a file_id column, a valid DRS id in every row
     (dg.4DFC/<uuid>) and the same row count as the original manifest
  4. Upload again from a fresh copy: every file gets the same file_id as in the first run

The CLI reads the data files from InputFiles/.../DataFiles and gets its own copy of the manifest folder's
tsv and txt files under tmp_path for each run (upload_files_via_cli), so -final.tsv is written there and the
repo is not changed (Katalon writes -final.tsv into InputFiles and deletes the stale one first).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submission_details import DS_AUTOMATION_STUDY_CREATE, DataSubmissionDetailPage
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.utils.cli_verifications import verify_final_manifest, verify_final_manifest_deterministic
from crdc_pw.pages.cli_uploader import require_submitter_token, upload_files_via_cli

log = logging.getLogger("crdc_pw.tc1405_101")

TC_NAME = "CRDCDH-1405_TC101"

pytestmark = [pytest.mark.CRDC_Smoke, pytest.mark.CRDC_DSFlow]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC101_CRDCDH_1405_CLINoFileIdVerifyFinalManifest(hub: Hub, tmp_path: Path) -> None:
    require_submitter_token(hub.settings)  # fail before a submission is created
    ds_list = DataSubmissionsListPage(hub)
    detail = DataSubmissionDetailPage(hub)

    # 1. Submitter: create the submission and read its id from the URL
    ds_list.open()
    submission_name = ds_list.create_data_submission("New", "both", "GC", DS_AUTOMATION_STUDY_CREATE)
    submission_id = detail.submission_id_from_url()
    log.info("Created submission %s (%s)", submission_name, submission_id)

    # 2. CLI upload of the data files, manifest without file_id
    first = upload_files_via_cli(hub.settings, submission_id, TC_NAME, "datafile", tmp_path / "run1")

    # 3. Final manifest: file_id column, valid DRS ids, same row count as the original
    verify_final_manifest(first)

    # 4. Same upload from a fresh copy: file_ids must not change
    second = upload_files_via_cli(hub.settings, submission_id, TC_NAME, "datafile", tmp_path / "run2")
    verify_final_manifest_deterministic(first, second)
