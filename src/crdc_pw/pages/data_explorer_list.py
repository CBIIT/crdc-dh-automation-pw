"""Data Explorer list (studies/explorer table).

Katalon: ``CRDC/NavBar/DataExplorer-Tab`` (via user menu). Reuses the same generic table
as Data Submissions list; filters use ``data-explorer-filters`` root."""

from __future__ import annotations

import logging

from playwright.sync_api import Locator

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.data_submission_details import DataSubmissionDetailPage
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.data_explorer_list")

_FILTERS = "CRDC/AILocators/DataExplorer/List/Filters/Filters-Container"
_LIST_ROW = "CRDC/AILocators/GenericTable/TableRow"


class DataExplorerListPage(BasePage):
    """Data Explorer generic-table list (filter bar + rows)."""

    @property
    def container(self) -> Locator:
        """Filter bar on the list. Visible means the explorer page has loaded."""
        return self._loc(_FILTERS)

    def open(self) -> None:
        """User menu → Data Explorer tab; wait for filter chrome."""
        log.info("Navigate: Data Explorer")
        HeaderPage(self._hub).open_data_explorer()
        self.container.wait_for(state="visible")
        log.info("Data Explorer list page loaded")

    def wait_for_list_table_settled(self) -> None:
        """Wait for Data Explorer filters and generic-table loading row to finish."""
        self.container.wait_for(state="visible")
        self.wait_for_generic_table_settled(self._loc(_LIST_ROW))

    def open_settled(self) -> None:
        """Open Data Explorer, then CircularProgress gone + generic table settled (PBAC DS view)."""
        HeaderPage(self._hub).open_data_explorer()
        DataSubmissionDetailPage(self._hub).wait_loading_spinner_gone()
        self.wait_for_list_table_settled()
        log.info("Data Explorer list open (settled)")
