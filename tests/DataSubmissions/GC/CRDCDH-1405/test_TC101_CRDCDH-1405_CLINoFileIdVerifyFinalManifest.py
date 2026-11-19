"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-1405/TC101_CRDC-1405-CLINoFileIdVerifyFinalManifest

`hub` starts signed in as Submitter.
No ValidationReport (Katalon generateValidationReport omitted in Playwright port).

Needs SubmitterApiToken in config/<profile>.yaml (the test fails with a clear message when it is
empty) and the `cli` extra: pip install -e ".[cli]" (the CLI needs Python 3.13 or newer).

Flow:
  1. Submitter creates a New GC "both" (metadata and data files) submission and reads its id
  2. Upload the data files with the CLI, using a manifest that has no file_id column
  3. The CLI wrote <manifest>-final.tsv: it has a file_id column, a valid DRS id in every row
     (dg.4DFC/<uuid>) and the same row count as the original manifest
  4. Upload again from a fresh copy: every file gets the same file_id as in the first run

Each CLI run works on its own copy of InputFiles/.../DataFiles under tmp_path, so the repo is not
changed (Katalon writes -final.tsv into InputFiles and deletes the stale one first).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submission_details import DS_AUTOMATION_STUDY_CREATE, DataSubmissionDetailPage
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.utils.cli_manifest import (
    diff_file_ids_between_runs,
    diff_final_manifest,
    final_manifest_path,
    read_manifest,
)
from crdc_pw.utils.cli_uploader import TYPE_DATA_FILE, CliResult, build_config, cli_output_problems, run_uploader
from crdc_pw.utils.validation_results import metadata_dir

log = logging.getLogger("crdc_pw.tc1405_101")

TC_NAME = "CRDCDH-1405_TC101"
MANIFEST_NAME = "manifest.tsv"

pytestmark = [pytest.mark.CRDC_Smoke, pytest.mark.CRDC_DSFlow]


def _upload_with_cli(hub: Hub, submission_id: str, run_dir: Path) -> tuple[CliResult, Path]:
    """Copy the input DataFiles into run_dir, run the CLI on the copy, return its result and the copied manifest."""
    data_dir = run_dir / "DataFiles"
    shutil.copytree(metadata_dir(TC_NAME) / "DataFiles", data_dir)
    manifest = data_dir / MANIFEST_NAME
    config = build_config(
        api_url=hub.settings.api_url,
        token=hub.settings.submitter_api_token,
        submission_id=submission_id,
        upload_type=TYPE_DATA_FILE,
        data_dir=data_dir,
        manifest=manifest,
    )
    result = run_uploader(config, run_dir / "cli")
    return result, manifest


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC101_CRDCDH_1405_CLINoFileIdVerifyFinalManifest(hub: Hub, tmp_path: Path) -> None:
    assert hub.settings.submitter_api_token, (
        f"SubmitterApiToken is empty in {hub.settings.config_path.name}. "
        "Add it (from the Katalon profile) so the upload CLI can run."
    )
    ds_list = DataSubmissionsListPage(hub)
    detail = DataSubmissionDetailPage(hub)

    # 1. Submitter: create the submission and read its id from the URL
    ds_list.open()
    submission_name = ds_list.create_data_submission(
        "New", "both", "GC", DS_AUTOMATION_STUDY_CREATE
    )
    submission_id = detail.submission_id_from_url()
    log.info("Created submission %s (%s)", submission_name, submission_id)

    # 2. CLI upload of the data files, manifest without file_id
    first_result, first_manifest = _upload_with_cli(hub, submission_id, tmp_path / "run1")
    problems = cli_output_problems(first_result)
    assert not problems, "CLI upload problems:\n" + "\n".join(problems) + f"\nOutput:\n{first_result.output}"
    log.info("Assert CLI upload run 1 succeeded")

    # 3. Final manifest: file_id column, valid DRS ids, same row count as the original
    first_final_path = final_manifest_path(first_manifest)
    assert first_final_path.is_file(), f"Final manifest not found: {first_final_path}"
    original = read_manifest(first_manifest)
    first_final = read_manifest(first_final_path)
    log.info("Original manifest headers %s, %s rows", original[0], len(original[1]))
    log.info("Final manifest headers %s, %s rows", first_final[0], len(first_final[1]))
    problems = diff_final_manifest(original, first_final)
    assert not problems, "Final manifest problems:\n" + "\n".join(problems)
    log.info("Assert final manifest has valid file_id values for all %s rows", len(first_final[1]))

    # 4. Same upload from a fresh copy: file_ids must not change
    second_result, second_manifest = _upload_with_cli(hub, submission_id, tmp_path / "run2")
    problems = cli_output_problems(second_result)
    assert not problems, "CLI re-upload problems:\n" + "\n".join(problems) + f"\nOutput:\n{second_result.output}"
    second_final_path = final_manifest_path(second_manifest)
    assert second_final_path.is_file(), f"Final manifest not found after re-upload: {second_final_path}"
    second_final = read_manifest(second_final_path)
    problems = diff_file_ids_between_runs(first_final, second_final)
    assert not problems, "file_id differs between runs:\n" + "\n".join(problems)
    log.info("Assert file_ids are identical across both runs")
