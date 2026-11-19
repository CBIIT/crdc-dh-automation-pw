"""Data Explorer study view (metadata table for one released study).

Reached from the Data Explorer list by clicking the first study link
(DataExplorerListPage.first_study_link). Katalon: DataExplorer.verifyDataExplorerMetadataView,
split here into locator properties, generic actions and readers. The comparison with the
expected TSV is utils/data_explorer_results.py, and the test owns the steps.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Locator

from crdc_pw.pages.base import BasePage

log = logging.getLogger("crdc_pw.data_explorer_study")

_CONTAINER = "CRDC/AILocators/DataExplorer/StudyView/Container"
_TITLE_SUFFIX = "CRDC/AILocators/DataExplorer/StudyView/Title-Suffix"
_NODE_TYPE_DDN = "CRDC/AILocators/DataExplorer/StudyView/NodeType-Ddn"
_NODE_TYPE_OPTION = "CRDC/AILocators/DataExplorer/StudyView/NodeType-Option"
_COLUMN_VISIBILITY = "CRDC/AILocators/DataExplorer/StudyView/ColumnVisibility-Btn"
_SHOW_ALL = "CRDC/AILocators/DataExplorer/StudyView/ShowAll-Chkbx"
_HEADER_CELL = "CRDC/AILocators/GenericTable/HeaderCell"
_TABLE_ROW = "CRDC/AILocators/GenericTable/TableRow"

# Header text, or the data-testid suffix when the cell has no text (Katalon getTableHeaderNames).
_HEADER_NAMES_JS = """
cells => cells.map(cell => {
    const text = (cell.innerText || '').replace(/\\s+/g, ' ').trim();
    return text || (cell.getAttribute('data-testid') || '').replace('generic-table-header-', '');
})
"""


class DataExplorerStudyPage(BasePage):
    """Study view: Node Type dropdown, column visibility and the metadata generic table."""

    @property
    def container(self) -> Locator:
        """Study view root. Visible means the metadata view has loaded."""
        return self._loc(_CONTAINER)

    @property
    def title_study_name(self) -> Locator:
        """Study name in the page title ("Data Explorer for Study - <name>")."""
        return self._loc(_TITLE_SUFFIX)

    @property
    def column_visibility_button(self) -> Locator:
        return self._loc(_COLUMN_VISIBILITY)

    def select_node_type(self, node: str) -> None:
        """Open the Node Type dropdown, click the option, and wait for that node's data to load.

        Katalon waits a fixed second here. The Hub fetches the node's properties a moment after the
        click and, when they arrive, resets the visible columns to the defaults. Opening Column
        visibility before then lets that reset undo Show All, so wait for the properties response,
        then the spinner and table loading row.

        The study view opens on its first node type, so that option is already selected: clicking it
        only closes the menu and sends no request, so skip the response wait. Either way, wait for a
        header cell, so the study's own first load has finished before the caller touches Column visibility.
        """
        log.info("Data Explorer: select node type %r", node)
        self._loc(_NODE_TYPE_DDN).first.click()
        option = self._loc(_NODE_TYPE_OPTION, node=node).first
        if option.get_attribute("aria-selected") == "true":
            option.click()
        else:
            self.click_and_wait_for_graphql(option, "retrievePropsForNodeType", nodeType=node)
        self.wait_loading_gone()
        self._loc(_HEADER_CELL).first.wait_for(state="visible")

    def check_show_all(self) -> None:
        """Check Show All in the open Column visibility menu (Katalon WebUI.check).

        The test id may sit on the MUI root rather than the input, so use the inner input then.
        """
        box = self._loc(_SHOW_ALL).first
        if box.evaluate("el => el.tagName") != "INPUT":
            box = box.locator("input").first
        box.check()

    def wait_loading_gone(self) -> None:
        """Wait out the Hub spinner and the generic-table loading row (Katalon waitForElementToDisappear x2)."""
        self.wait_loading_spinner_gone()
        self.wait_for_generic_table_settled()

    def read_headers(self) -> list[str]:
        """Column header names in table order."""
        names: list[str] = self._loc(_HEADER_CELL).evaluate_all(_HEADER_NAMES_JS)
        return names

    def read_rows(self) -> list[list[str]]:
        """Every data row as a list of cell text (full text for truncated cells)."""
        return self._read_table_rows_full_text(self._loc(_TABLE_ROW))
