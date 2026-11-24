"""Xray CRDCDH-4027 — SDM in the Create a Data Submission dialog (story CRDCDH-3921). Phase 1.

What this checks
    A Submitter who opens Create a Data Submission must see SDM in the Data Commons dropdown,
    after the existing models. The other half of the story (Model Navigator menu and downloads)
    is in test_TC_CRDCDH-4027_SdmIntegration.py, which logs in as Admin. This file is separate
    because it needs a Submitter: the Create a Data Submission button is a Submitter action, and
    the repo keeps one test per file.

Where the expected values come from
    The Hub builds the dropdown from cache/content.json on the tier branch (qa, qa2, dev) of
    CBIIT/crdc-datahub-models: every model that is not hidden, sorted by its order field
    (GC, CTDC, ICDC, PSDC, SDM). The test fetches that file (crdc_pw.utils.model_content) and
    compares, so nothing is typed into the test.

Nothing is created and nothing is downloaded. The dialog is opened, read, and closed again.

Flow (Submitter):
  1. Data Submissions > Create a Data Submission > Data Commons dropdown lists the visible
     models in manifest order
  2. SDM is the last option and comes after PSDC
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.utils.model_content import fetch_model_content, visible_display_names

log = logging.getLogger("crdc_pw.tc_crdcdh_4027_create_dialog")

SDM = "SDM"

pytestmark = pytest.mark.CRDC_Auxiliary


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC_CRDCDH_4027_SdmCreateDialogDataCommons(hub: Hub) -> None:
    # Setup: the manifest gives the expected Data Commons list. Here the names are the plain
    # display names ("GC", "CTDC", "ICDC", "PSDC", "SDM"), not the "<name> Model" menu labels.
    content = fetch_model_content(hub.settings.profile)
    ds_list = DataSubmissionsListPage(hub)
    ds_list.open()

    # 1. Click Create a Data Submission, open the Data Commons dropdown, read every option in the
    #    order shown, then close the dialog without creating anything. The dropdown shows the
    #    visible models in manifest order.
    options = ds_list.read_create_dialog_data_commons_options()
    expected = visible_display_names(content)
    assert options == expected, f"Create dialog Data Commons {options}, manifest says {expected}"

    # 2. The story's ordering rule: SDM goes at the bottom, below PSDC (PSDC is order 5, SDM 6).
    assert options[-1] == SDM, f"SDM must be last, got {options}"
    assert "PSDC" in options and options.index("PSDC") < options.index(SDM), options

    log.info("PASS CRDCDH-4027 Create dialog: %s on profile=%s", options, hub.settings.profile)
