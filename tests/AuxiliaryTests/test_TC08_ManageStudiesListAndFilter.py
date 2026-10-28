"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC08_ManageStudiesListAndFilter

`hub` is already signed in as Admin (fixture). This file is the scenario after login.

Flow:
  1. Open Manage Studies from the header
  2. Check the list is up (container + Add Study)
  3. Filter by study name autoQA and program AutoTest-Program
  4. Assert at least one row, and some cell contains autoQA
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.pages.studies import ADD_STUDY, CONTAINER, StudiesListPage

log = logging.getLogger("crdc_pw.tc08")


@pytest.mark.smoke
def test_TC08_ManageStudiesListAndFilter(hub: Hub) -> None:
    studies = StudiesListPage(hub.page, hub.locators)

    # 1. User menu → Manage Studies
    studies.open()

    # 2. List chrome: container and Add Study are visible (0 rows is allowed here)
    expect(studies.loc(CONTAINER)).to_be_visible()
    expect(studies.loc(ADD_STUDY)).to_be_visible()
    studies.wait_for_table_settled()
    rows = studies.row_count()
    log.info("Assert Manage Studies: container and Add Study visible (rows=%s)", rows)

    # 3. Filter to the autoQA study under AutoTest-Program (same values as Katalon)
    studies.apply_filters(study_name="autoQA", program="AutoTest-Program")

    # 4. Filtered table: at least one row, and a cell contains "autoQA"
    filtered = studies.read_table_rows()
    count = len(filtered)
    log.info("Manage Studies table row count: %s", count)
    assert count >= 1, f"expected at least 1 rows, got {count}"
    log.info("Assert Manage Studies: row count >= 1 (actual=%s)", count)

    found = any("autoQA" in (cell or "") for row in filtered for cell in row)
    assert found, "no row contains 'autoQA'"
    log.info("Assert Manage Studies: a row contains %r", "autoQA")
    log.info("Assert Manage Studies filter results: completed; rows=%s", count)

    log.info("PASS TC08: Manage Studies list filtered to autoQA as %s", hub.role)
