"""Data Explorer list (studies/explorer table).

Katalon: ``CRDC/NavBar/DataExplorer-Tab`` (header nav, same chrome as Data Submissions).
Reuses the same generic table as Data Submissions list; filters use ``data-explorer-filters`` root."""

from __future__ import annotations

import logging

from playwright.sync_api import Locator

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.data_explorer_list")

_FILTERS = "CRDC/AILocators/DataExplorer/List/Filters/Filters-Container"
_LIST_ROW = "CRDC/AILocators/GenericTable/TableRow"
_STUDY_NAME = "CRDC/AILocators/DataExplorer/List/Filters/StudyName-TxtBx"
_FIRST_STUDY_LINK = "CRDC/AILocators/DataExplorer/StudyView/DataSubmissionName-Link"


class DataExplorerListPage(BasePage):
    """Data Explorer generic-table list (filter bar + rows)."""

    @property
    def container(self) -> Locator:
        """Filter bar on the list. Visible means the explorer page has loaded."""
        return self._loc(_FILTERS)

    @property
    def first_study_link(self) -> Locator:
        """Link in the first list row (Katalon StudyView/DataSubmissionName-Link). Opens the study view."""
        return self._loc(_FIRST_STUDY_LINK)

    def fill_study_name(self, value: str) -> None:
        """Type into the Study Name filter, then wait for the list to reload (Katalon sendKeys + delay).

        Waits for the first unfiltered load before taking the "before" snapshot. Without it the
        initial load looked like the filter result and the first study (not the filtered one) was opened.
        """
        rows = self._loc(_LIST_ROW)
        self.wait_for_list_table_settled()
        rows.first.wait_for(state="visible")
        before = self._table_fingerprint(rows)
        self._loc(_STUDY_NAME).first.fill(value)
        self.wait_for_generic_table_settled(rows, previous=before)
        log.info("Data Explorer list filtered by study name %r", value)

    def open(self) -> None:
        """Nav bar Data Explorer tab; wait for filter chrome."""
        log.info("Navigate: Data Explorer")
        HeaderPage(self._hub).open_data_explorer()
        self.container.wait_for(state="visible")
        log.info("Data Explorer list page loaded")

    def wait_for_list_table_settled(self) -> None:
        """Wait for Data Explorer filters and generic-table loading row to finish."""
        self.container.wait_for(state="visible")
        self.wait_for_generic_table_settled(self._loc(_LIST_ROW))

    def table_data_rows(self) -> Locator:
        """Generic table body rows (PBAC ``data_submission:view``)."""
        return self._loc(_LIST_ROW)

    def open_settled(self) -> None:
        """Open Data Explorer, then CircularProgress gone + generic table settled (PBAC DS view)."""
        HeaderPage(self._hub).open_data_explorer()
        self.wait_loading_spinner_gone()
        self.wait_for_list_table_settled()
        log.info("Data Explorer list open (settled)")
