"""Katalon: Test Cases/CRDC/AuxiliaryTests/TC04_PaginationVerification (DS = Data Submissions list)

`hub` is already signed in as Data Commons Personnel (fixture). This file is the scenario after login.

Flow:
  1. Open Data Submissions from the header and wait for the table
  2. Rows-per-page offers 5, 10, 20 and 50
  3. Default rows per page is 20
  4. "from-to of total" label is well formed and matches the rows shown
  5. Previous, Next, page-number buttons and the first and last page edges work
  6. Change rows per page to 5: select, row count and label all follow
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage

log = logging.getLogger("crdc_pw.tc04")

pytestmark = [pytest.mark.CRDC_Auxiliary, pytest.mark.CRDC_Smoke]


@pytest.mark.parametrize("hub", ["Dcp"], indirect=True)
def test_TC04_DSPaginationVerification(hub: Hub) -> None:
    ds_list = DataSubmissionsListPage(hub)

    # 1. Nav bar -> Data Submissions, table loaded
    ds_list.open()
    ds_list.wait_for_list_table_settled()

    # 2. Rows-per-page options
    ds_list.verify_rows_per_page_options([5, 10, 20, 50])
    log.info("Assert Data Submissions: rows-per-page options 5, 10, 20, 50")

    # 3. Default rows per page
    ds_list.verify_default_rows_per_page(20)
    log.info("Assert Data Submissions: default rows per page 20")

    # 4. Displayed-rows label
    ds_list.verify_displayed_rows_text()
    log.info("Assert Data Submissions: displayed rows text matches the page")

    # 5. Page navigation (ends back on page 1)
    ds_list.verify_page_navigation()
    log.info("Assert Data Submissions: page navigation")

    # 6. Rows per page 5
    ds_list.verify_rows_per_page_change(5)
    log.info("Assert Data Submissions: rows per page changed to 5")
