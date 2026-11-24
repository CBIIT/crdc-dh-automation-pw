"""Xray CRDCDH-4027 — SDM in the Create a Data Submission dialog, a new SDM submission and its metadata (story CRDCDH-3921). Phases 2 and 3.

What this checks
    A Submitter must be able to pick SDM as the Data Commons, create a metadata-only submission
    for it, see SDM named on the submission, and upload metadata that is checked against the SDM
    model. The other half of the story (Model Navigator menu and downloads) is in
    test_TC_CRDCDH-4027_SdmIntegration.py, which logs in as Admin. This file is separate because
    it needs a Submitter, and the repo keeps one test per file.

Where the expected values come from
    The dropdown list and the model version come from cache/content.json on the tier branch (qa,
    qa2, dev) of CBIIT/crdc-datahub-models (crdc_pw.utils.model_content): every model that is
    not hidden, sorted by its order field (GC, CTDC, ICDC, PSDC, SDM), and SDM's current-version
    (0.0.3 at the time of writing). The expected upload error comes from the files under
    InputFiles/CRDC/MetadataData/CRDCDH-4027_UnknownNode/expected.

What this test creates and uploads
    It creates one real submission on the Hub: New, metadata only, Data Commons SDM, study
    "autoQA - AutomationQA_Study", named auto-test_<timestamp> (generated, so reruns never
    collide). Nothing is deleted afterwards, as with the other Data Submission tests.
    Upload 1 (always): InputFiles/CRDC/MetadataData/CRDCDH-4027_UnknownNode/SDM_notanode_v0.0.3.tsv
      A single row whose type is "notanode", which is not a node of the SDM model. The Hub must
      answer: SDM_notanode_v0.0.3.tsv: 2": Node type "notanode" is not defined.
      That proves the Hub loaded the SDM model and checks uploaded rows against it.
    Upload 2 (only when VERIFY_SDM_DATA_VALIDATION is True): the three TSVs in
      InputFiles/CRDC/MetadataData/CRDCDH-4027:
        SDM_program_v0.0.3.tsv      one row with every required program property
        SDM_study_v0.0.3.tsv        one row with every required study property
        SDM_participant_v0.0.3.tsv  two rows; the second has no ncbi_tax_id (required) on purpose

Flow (Submitter):
  1. Data Submissions > Create a Data Submission > Data Commons dropdown lists the visible
     models in manifest order (nothing is created yet; the dialog is closed again)
  2. SDM is the last option and comes after PSDC
  3. Create a New SDM metadata-only submission; the header Data Commons reads SDM
  4. Step 1 UPLOAD METADATA reads "SDM Data Model: v<current-version>"
  5. Upload the unknown-node TSV; Upload Activities shows one Metadata batch, 1 file, Failed, and
     the Upload Errors modal shows the "Node type is not defined" message
  6. (flag) Check the expected Validation Results files and the SDM mapping exist (fail if not),
     upload the three SDM TSVs, click Validate, compare the Validation Results table with the
     expected files. TURNED OFF for now, see VERIFY_SDM_DATA_VALIDATION below.
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submission_details import DS_AUTOMATION_STUDY_CREATE, DataSubmissionDetailPage
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.utils.model_content import current_version, fetch_model_content, visible_display_names
from crdc_pw.utils.validation_results import (
    list_nodes_from_expected_validation_results_folder,
    load_validation_results_mappings,
)

log = logging.getLogger("crdc_pw.tc_crdcdh_4027_create_and_validate")

SDM = "SDM"

# Metadata folders under InputFiles/CRDC/MetadataData. See the module docstring for the files.
TC_UNKNOWN_NODE = "CRDCDH-4027_UnknownNode"
TC_SDM_DATA = "CRDCDH-4027"

# Step 6 uploads real SDM metadata, validates it and compares the Validation Results table. It is
# off because the Hub cannot validate SDM metadata yet. On 24 Nov 2026 on QA, every upload of a
# TSV whose type is a real SDM node (program, study or participant, alone or together) ends in a
# Failed batch with "Batch validation failed - internal error", and the dev team says validation
# may not work as expected for now. Set this to True once it works. Still to add at that point:
# expected-ValidationResults files under InputFiles/CRDC/MetadataData/CRDCDH-4027 and rows in the
# SDM sheet of DSV_ValidationResults-mappings.xlsx (node, then the identifier column the Validation
# Results table shows). The SDM sheet exists but is empty on purpose, like the PSDC sheet. The shared compare (verify_validation_results_vs_expected_for_tc, same as
# Katalon) logs a skip and passes when a folder has no expected files, so step 6 checks first that
# the expected files and the SDM mapping exist and fails with a message if they do not. Turning the
# flag on without adding that data therefore cannot pass quietly.
VERIFY_SDM_DATA_VALIDATION = False

pytestmark = pytest.mark.CRDC_Auxiliary


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC_CRDCDH_4027_SdmCreateAndValidate(hub: Hub) -> None:
    # Setup: the manifest gives the expected Data Commons list and SDM's version. The dropdown
    # names are the plain display names ("GC", "CTDC", "ICDC", "PSDC", "SDM").
    content = fetch_model_content(hub.settings.profile)
    version = current_version(content, SDM)
    ds_list = DataSubmissionsListPage(hub)
    detail = DataSubmissionDetailPage(hub)
    ds_list.open()

    # 1. Click Create a Data Submission, open the Data Commons dropdown, read every option in the
    #    order shown, then close the dialog without creating anything. This runs first so a
    #    manifest or deploy problem fails fast, before a submission is created.
    options = ds_list.read_create_dialog_data_commons_options()
    expected = visible_display_names(content)
    assert options == expected, f"Create dialog Data Commons {options}, manifest says {expected}"

    # 2. The story's ordering rule: SDM goes at the bottom, below PSDC (PSDC is order 5, SDM 6).
    assert options[-1] == SDM, f"SDM must be last, got {options}"
    assert "PSDC" in options and options.index("PSDC") < options.index(SDM), options

    # 3. Create the submission: New, metadata only, Data Commons SDM. The page object fills the
    #    dialog, creates it and opens it on its Upload Activities page. The summary header at
    #    the top of the page must then show Data Commons = SDM (the other header fields are not
    #    checked here).
    submission_name = ds_list.create_data_submission("New", "metadata only", SDM, DS_AUTOMATION_STUDY_CREATE)
    log.info("Created SDM submission %s", submission_name)
    detail.verify_summary_header_fields({"data_commons": SDM, "submission_name": submission_name})

    # 4. Step 1 UPLOAD METADATA names the model and its version: "SDM Data Model: v0.0.3". The
    #    page shows it in capitals, but the element text is mixed case, which is what is compared.
    expect(detail.upload_model_version).to_have_text(f"SDM Data Model: v{version}")

    # 5. Upload the one-row TSV whose type is "notanode" (not an SDM node). Upload Activities must
    #    show one Metadata batch with 1 file and status Failed, and the Upload Errors modal must
    #    show exactly the message in CRDCDH-4027_UnknownNode/expected. The modal is opened and
    #    closed by the page object. This is the check that the Hub validates uploads against SDM.
    detail.upload_folder(TC_UNKNOWN_NODE)
    detail.verify_upload_activities_batch_row("Metadata", 1, "Failed")
    detail.verify_upload_errors_modal(TC_UNKNOWN_NODE)
    log.info("SDM Hub rejects an undefined node type as expected for %s", submission_name)

    # 6. Real SDM metadata: upload the three TSVs, click Validate (waits up to 5 minutes), then
    #    compare the Validation Results table with the expected files per node, severity and
    #    issue type. Only runs when VERIFY_SDM_DATA_VALIDATION is True.
    if VERIFY_SDM_DATA_VALIDATION:
        # 6a. Guard, before anything is uploaded: the expected data must exist. The shared compare
        #     below silently skips a folder with no expected files, and a missing SDM mapping sheet
        #     only logs a warning, so without this a run could pass while checking nothing.
        nodes = list_nodes_from_expected_validation_results_folder(TC_SDM_DATA)
        assert nodes, (
            f"VERIFY_SDM_DATA_VALIDATION is on but InputFiles/CRDC/MetadataData/{TC_SDM_DATA}/"
            "expected-ValidationResults has no *_expected-ValidationResults.tsv files. Add them first."
        )
        mappings = load_validation_results_mappings(SDM)
        unmapped = [node for node in nodes if node not in mappings]
        assert not unmapped, (
            f"No SDM mapping for node(s) {unmapped}. Add an SDM sheet (node, identifier column) "
            "to InputFiles/CRDC/DataSubmissionValidation/DSV_ValidationResults-mappings.xlsx."
        )

        # 6b. Upload the three TSVs, validate, compare the Validation Results table.
        detail.upload_folder(TC_SDM_DATA)
        detail.click_validate()
        detail.verify_validation_results_vs_expected_for_tc(TC_SDM_DATA, model=SDM)
    else:
        log.info("Skip SDM data validation steps (VERIFY_SDM_DATA_VALIDATION is False)")

    log.info(
        "PASS CRDCDH-4027 create and validate: %s, SDM v%s, options %s, as %s on profile=%s",
        submission_name,
        version,
        options,
        hub.role,
        hub.settings.profile,
    )
