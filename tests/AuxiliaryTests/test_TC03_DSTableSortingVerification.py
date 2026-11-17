"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC03_TableSortingVerification (DS = Data Submissions list)

`hub` is already signed in as Data Commons Personnel (fixture). This file is the scenario after login.

Flow:
  1. Open Data Submissions from the header and wait for the table
  2. Every column is sortable except SRF
  3. Default sort is Last Updated, newest first, and the rows are in that order
  4. Click Status: sorts one way, click again: sorts the other way (rows checked each time)
  5. Same for Data Commons
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage

log = logging.getLogger("crdc_pw.tc03")

pytestmark = [pytest.mark.CRDC_Auxiliary, pytest.mark.CRDC_Smoke]


@pytest.mark.parametrize("hub", ["Dcp"], indirect=True)
def test_TC03_DSTableSortingVerification(hub: Hub) -> None:
    ds_list = DataSubmissionsListPage(hub)

    # 1. Nav bar -> Data Submissions, table loaded
    ds_list.open()
    ds_list.wait_for_list_table_settled()

    # 2. Sortable columns: all except SRF
    ds_list.verify_column_sortability(["SRF"])
    log.info("Assert Data Submissions: column sortability (non-sortable: SRF)")

    # 3. Default sort
    ds_list.verify_default_sort("Last Updated", "desc")
    log.info("Assert Data Submissions: default sort Last Updated desc")

    # 4. Click-to-sort: Status
    ds_list.verify_column_sort_on_click("Status")
    log.info("Assert Data Submissions: Status sorts both ways")

    # 5. Click-to-sort: Data Commons
    ds_list.verify_column_sort_on_click("Data Commons")
    log.info("Assert Data Submissions: Data Commons sorts both ways")
