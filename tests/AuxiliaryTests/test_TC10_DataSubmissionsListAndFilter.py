"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC10_DataSubmissionsListAndFilter

`hub` is already signed in as Submitter (fixture). This file is the scenario after login.

Flow:
  1. Open Data Submissions from the header
  2. Check the list is up (table + Create button)
  3. Filter: name auto, status Submitted + In Progress, program AutoTest-Program,
     submitter pbac.submitter-automation, data commons GC
  4. Assert at least one row, and every row matches the filters (name auto*, data commons GC,
     status Submitted or In Progress), checked by column header
  5. Reset filters
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage

log = logging.getLogger("crdc_pw.tc10")

pytestmark = [pytest.mark.CRDC_Auxiliary, pytest.mark.CRDC_Smoke]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC10_DataSubmissionsListAndFilter(hub: Hub) -> None:
    ds_list = DataSubmissionsListPage(hub)

    # 1. Nav bar -> Data Submissions
    ds_list.open()

    # 2. List chrome: table and Create button are visible (0 rows is allowed here)
    expect(ds_list.table).to_be_visible()
    expect(ds_list.create_button).to_be_visible()
    ds_list.wait_for_table_settled()
    rows = ds_list.table_data_rows().count()
    log.info("Assert Data Submissions: table and Create button visible (rows=%s)", rows)

    # 3. Same filter values as Katalon (empty dbGaP is skipped)
    ds_list.apply_filters(
        submission_name="auto",
        status="Submitted, In Progress",
        program="AutoTest-Program",
        submitter_name="pbac.submitter-automation Please Do Not Edit",
        data_commons="GC",
        dbgap="",
    )

    # 4. Filtered table: at least one row, and a cell contains "auto"
    filtered = ds_list.read_table_rows()
    count = len(filtered)
    log.info("Data Submissions table row count: %s", count)
    assert count >= 1, f"expected at least 1 rows, got {count}"
    log.info("Assert Data Submissions: row count >= 1 (actual=%s)", count)

    # Every row must satisfy each filter, checked in the column that filter targets. A cell-anywhere
    # match is too loose: the Submitter column ("...-automation") also contains "auto".
    headers = ds_list.read_table_headers()
    for column in ("Submission Name", "Data Commons", "Status"):
        assert column in headers, f"column {column!r} not in table headers {headers}"
    name_i = headers.index("Submission Name")
    commons_i = headers.index("Data Commons")
    status_i = headers.index("Status")
    allowed_status = {"Submitted", "In Progress"}
    for row in filtered:
        name, commons, status = row[name_i], row[commons_i], row[status_i]
        assert name.lower().startswith("auto"), f"submission name {name!r} does not start with 'auto'"
        assert commons == "GC", f"data commons {commons!r} is not 'GC' (submission {name!r})"
        assert status in allowed_status, f"status {status!r} not in {sorted(allowed_status)} (submission {name!r})"
    log.info(
        "Assert Data Submissions: all %s rows have name auto*, data commons GC, status in %s",
        count,
        sorted(allowed_status),
    )
    log.info("Assert Data Submissions filter results: completed; rows=%s", count)

    # 5. Clear filters
    ds_list.reset_filters()

    log.info("PASS TC10: Data Submissions list filtered and reset as %s", hub.role)
