"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC09_ManageProgramsListAndFilter

`hub` is already signed in as Admin (fixture). This file is the scenario after login.

Flow:
  1. Open Manage Programs from the header
  2. Check the list is up (container + Add Program)
  3. Filter by program AutoTest and study autoQA
  4. Assert at least one row, and some cell contains auto
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.pages.programs import ProgramsListPage

log = logging.getLogger("crdc_pw.tc09")

pytestmark = [pytest.mark.CRDC_Auxiliary, pytest.mark.CRDC_Smoke]


def test_TC09_ManageProgramsListAndFilter(hub: Hub) -> None:
    programs = ProgramsListPage(hub.page, hub.locators)

    # 1. User menu → Manage Programs
    programs.open()

    # 2. List chrome: container and Add Program are visible (0 rows is allowed here)
    expect(programs.container).to_be_visible()
    expect(programs.add_program).to_be_visible()
    programs.wait_for_table_settled()
    rows = programs.row_count()
    log.info("Assert Manage Programs: container and Add Program visible (rows=%s)", rows)

    # 3. Filter to AutoTest / autoQA (same values as Katalon)
    programs.apply_filters(program_name="AutoTest", study_name="autoQA")

    # 4. Filtered table: at least one row, and a cell contains "auto"
    filtered = programs.read_table_rows()
    count = len(filtered)
    log.info("Manage Programs table row count: %s", count)
    assert count >= 1, f"expected at least 1 rows, got {count}"
    log.info("Assert Manage Programs: row count >= 1 (actual=%s)", count)

    found = any("auto" in (cell or "") for row in filtered for cell in row)
    assert found, "no row contains 'auto'"
    log.info("Assert Manage Programs: a row contains %r", "auto")
    log.info("Assert Manage Programs filter results: completed; rows=%s", count)

    log.info("PASS TC09: Manage Programs list filtered to AutoTest/autoQA as %s", hub.role)
