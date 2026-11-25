"""Data Explorer list (studies/explorer table).

Katalon: ``CRDC/NavBar/DataExplorer-Tab`` (header nav, same chrome as Data Submissions).
Reuses the same generic table as Data Submissions list; filters use ``data-explorer-filters`` root."""

from __future__ import annotations

import logging

from playwright.sync_api import Locator
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.data_explorer_list")

_FILTERS = "CRDC/AILocators/DataExplorer/List/Filters/Filters-Container"
_LIST_ROW = "CRDC/AILocators/GenericTable/TableRow"
_STUDY_NAME = "CRDC/AILocators/DataExplorer/List/Filters/StudyName-TxtBx"
_FIRST_STUDY_LINK = "CRDC/AILocators/DataExplorer/StudyView/DataSubmissionName-Link"
_LIST_TABLE = "CRDC/AILocators/GenericTable/Table"
_DATA_COMMONS_DDN = "CRDC/AILocators/DataExplorer/List/Filters/DataCommons-Ddn"
_DATA_COMMONS_OPTION = "CRDC/AILocators/DataExplorer/List/Filters/DataCommons-Option"
_DATA_COMMONS_OPTIONS = "CRDC/AILocators/DataExplorer/List/Filters/DataCommons-Options"
_LISTBOX = "[role='listbox']"


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

    def read_data_commons_options(self) -> list[str]:
        """Open the Data Commons filter and return its options in order, without "All". Closes it again.

        The Hub lists only data commons that have released study data, so a model with no
        released study (for example a new one) is not in this list.

        The options come from the same data as the table, and "All" is shown at once, so the
        table must be loaded first or the list would be read short (seen: only "All").
        """
        self.wait_for_list_table_settled()
        self._loc(_LIST_ROW).first.wait_for(state="visible")
        self._loc(_DATA_COMMONS_DDN).first.click()
        options = self._loc(_DATA_COMMONS_OPTIONS)
        options.first.wait_for(state="visible")
        names = [" ".join(text.split()) for text in options.all_inner_texts()]
        self.page.keyboard.press("Escape")
        self.page.locator(_LISTBOX).first.wait_for(state="hidden")
        return [name for name in names if name and name != "All"]

    def apply_data_commons_filter(self, name: str) -> None:
        """Choose one Data Commons in the filter and wait for the list to reload.

        The menu is rendered inside the filter bar and its invisible backdrop can refuse a real
        click (seen on the Data Submissions filters, see DataSubmissionsListPage._select_list_option),
        so if the click is refused the click event is sent to the option instead.
        """
        rows = self._loc(_LIST_ROW)
        self.wait_for_list_table_settled()
        before = self._table_fingerprint(rows)
        self._loc(_DATA_COMMONS_DDN).first.click()
        option = self._loc(_DATA_COMMONS_OPTION, name=name).first
        option.wait_for(state="visible")
        try:
            option.click(timeout=self.PROBE_MS)
        except PlaywrightTimeoutError:
            log.info("Data Commons option %r click was blocked by the menu backdrop; dispatching click", name)
            option.dispatch_event("click")
        self.page.locator(_LISTBOX).first.wait_for(state="hidden")
        self.wait_for_generic_table_settled(rows, previous=before)
        log.info("Data Explorer list filtered by Data Commons %r", name)

    def read_table_headers(self) -> list[str]:
        """Column headers of the list in order, whitespace collapsed (for example "Data Commons")."""
        return self._read_table_headers(self._loc(_LIST_TABLE))

    def read_table_rows(self) -> list[list[str]]:
        """Every data row on the current page as cell texts in header order.

        Uses the full text of truncated cells, because the Data Commons cell is cut at 40
        characters on screen.
        """
        return self._read_table_rows_full_text(self._loc(_LIST_ROW))
