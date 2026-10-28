"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC09_ManageProgramsListAndFilter

`hub` is already signed in as Admin.
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.pages.programs import ADD_PROGRAM, CONTAINER, ProgramsListPage

log = logging.getLogger("crdc_pw.tc09")


@pytest.mark.smoke
def test_TC09_ManageProgramsListAndFilter(hub: Hub) -> None:
    programs = ProgramsListPage(hub.page, hub.locators)
    programs.open()

    expect(programs.loc(CONTAINER)).to_be_visible()
    expect(programs.loc(ADD_PROGRAM)).to_be_visible()
    programs.wait_for_table_settled()
    rows = programs.row_count()
    log.info("Assert Manage Programs: container and Add Program visible (rows=%s)", rows)

    programs.apply_filters(program_name="AutoTest", study_name="autoQA")

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
