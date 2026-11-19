"""Katalon: Test Cases/CRDC/DataSubmissions/GC/CRDCDH-3026/TC201_VerifyDataExplorerMetadataView

`hub` starts signed in as Submitter.
No ValidationReport (Katalon generateValidationReport omitted in Playwright port).

QA seed (manual prerequisite, as in Katalon): Hub study automation_CompletedStudy
(AutomationCompletedStudy) with the metadata in InputFiles/CRDC/MetadataData/CRDCDH-3026
uploaded, validated and released. This test does not create it.

Flow:
  1. Open Data Explorer, filter by the study acronym, open the first study in the list
     (the page title must show that study; this check is not in Katalon)
  2. For program, study, participant and sample: select the node type, show all columns,
     and the table (headers, row count, every cell) matches <node>.tsv in the expected folder
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_explorer_list import DataExplorerListPage
from crdc_pw.pages.data_explorer_study import DataExplorerStudyPage
from crdc_pw.utils.data_explorer_results import load_expected_data_explorer_table
from crdc_pw.utils.ui_helpers import assert_element_text

log = logging.getLogger("crdc_pw.tc3026_201")

TC_NAME = "CRDCDH-3026"
STUDY_FILTER = "automation_CompletedStudy"
NODE_TYPES = ("program", "study", "participant", "sample")

pytestmark = [pytest.mark.CRDC_Smoke, pytest.mark.CRDC_DSFlow]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC201_CRDCDH_3026_VerifyDataExplorerMetadataView(hub: Hub) -> None:
    explorer = DataExplorerListPage(hub)
    study = DataExplorerStudyPage(hub)

    # 1. Data Explorer list -> first study matching the filter
    explorer.open()
    explorer.fill_study_name(STUDY_FILTER)
    explorer.first_study_link.first.click()
    # Not in Katalon: fail clearly if the list was not filtered yet and another study opened
    assert_element_text(study.title_study_name, STUDY_FILTER)
    log.info("Opened the Data Explorer study %r", STUDY_FILTER)

    # 2. Each node type: select it, show all columns, compare the table with the expected TSV
    for node in NODE_TYPES:
        expected_headers, expected_rows = load_expected_data_explorer_table(TC_NAME, node)
        study.verify_node_table(node, expected_headers, expected_rows)
