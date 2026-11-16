"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC12_SubmissionRequestsListAndFilter

`hub` is already signed in as Submitter (fixture). This file is the scenario after login.

Flow:
  1. Open Submission Requests from the header
  2. Check the list is up (container + Start a Submission Request button)
  3. Filter: submitter name = the signed-in user, status New + In Progress
  4. Assert at least one row, and every row matches the filters (status New or In Progress,
     submitter is the signed-in user), checked by column header
  5. Reset filters
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage

log = logging.getLogger("crdc_pw.tc12")

pytestmark = [pytest.mark.CRDC_Auxiliary, pytest.mark.CRDC_Smoke]


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC12_SubmissionRequestsListAndFilter(hub: Hub) -> None:
    sr_list = SubmissionRequestsListPage(hub)

    # 1. Nav bar -> Submission Requests
    sr_list.open()

    # 2. List chrome: container and Start button are visible (0 rows is allowed here)
    expect(sr_list.container).to_be_visible()
    expect(sr_list.start_button).to_be_visible()
    rows = len(sr_list.read_table_rows())
    log.info("Assert Submission Requests: container and Start button visible (rows=%s)", rows)

    # 3. Filter to the signed-in user's New / In Progress requests (Katalon getProfileName)
    submitter = HeaderPage(hub).username()
    sr_list.apply_submission_requests_list_filters({"submitterName": submitter, "status": "New, In Progress"})

    # 4. Filtered table: at least one row, and every row satisfies each filter
    filtered = sr_list.read_table_rows()
    count = len(filtered)
    log.info("Submission Requests table row count: %s", count)
    assert count >= 1, f"expected at least 1 rows, got {count}"
    log.info("Assert Submission Requests: row count >= 1 (actual=%s)", count)

    # Check each filter in its own column (PW-only tightening; Katalon only asserts the count).
    headers = sr_list.read_table_headers()
    for column in ("Submitter Name", "Status"):
        assert column in headers, f"column {column!r} not in table headers {headers}"
    submitter_i = headers.index("Submitter Name")
    status_i = headers.index("Status")
    allowed_status = {"New", "In Progress"}
    for row in filtered:
        who, status = row[submitter_i], row[status_i]
        assert status in allowed_status, f"status {status!r} not in {sorted(allowed_status)} (submitter {who!r})"
        assert submitter.lower() in who.lower(), f"submitter {who!r} does not match signed-in user {submitter!r}"
    log.info(
        "Assert Submission Requests: all %s rows have submitter %r and status in %s",
        count,
        submitter,
        sorted(allowed_status),
    )
    log.info("Assert Submission Requests filter results: completed; rows=%s", count)

    # 5. Clear filters
    sr_list.reset_submission_requests_filters()

    log.info("PASS TC12: Submission Requests list filtered and reset as %s", hub.role)
