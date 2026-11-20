"""Data Explorer study view (metadata table for one released study).

Reached from the Data Explorer list by clicking the first study link
(DataExplorerListPage.first_study_link). Katalon: DataExplorer.verifyDataExplorerMetadataView,
split here into locator properties, generic actions and readers, plus verify_node_table (one node
per call, expected data supplied by the test). The expected-TSV loader and the diff are in
utils/data_explorer_results.py.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Locator, expect

from crdc_pw.pages.base import BasePage
from crdc_pw.utils.data_explorer_results import diff_data_explorer_table, map_expected_headers_to_ui

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

    def show_all_columns(self) -> None:
        """Open Column visibility, check Show All, and wait for the table to settle."""
        self.column_visibility_button.first.click()
        self.check_show_all()
        self.wait_loading_gone()
        expect(self.container.first).to_be_visible()

    def verify_node_table(self, node: str, expected_headers: list[str], expected_rows: list[list[str]]) -> None:
        """Select the node, show all columns, and assert the table matches the expected data.

        The test supplies the expected headers and rows. The page reads the table and compares.
        Katalon: DataExplorer.verifyDataExplorerMetadataView, one node per call.
        """
        self.select_node_type(node)
        self.show_all_columns()
        ui_headers = self.read_headers()
        ui_rows = self.read_rows()
        # Show All adds UI-only columns (crdc_id, *_concept_code, ...). Log the actual row narrowed to
        # the expected columns, in the same order, so the two lines line up cell for cell.
        mapping = map_expected_headers_to_ui(expected_headers, ui_headers)
        ui_only = [h for i, h in enumerate(ui_headers) if i not in mapping]
        log.info("Node %r: expected headers (%s) %s", node, len(expected_headers), expected_headers)
        log.info("Node %r: UI headers (%s) %s", node, len(ui_headers), ui_headers)
        log.info("Node %r: UI-only columns, not checked (%s) %s", node, len(ui_only), ui_only)
        log.info("Node %r: expected %s rows, actual %s rows", node, len(expected_rows), len(ui_rows))
        if expected_rows and ui_rows:
            narrowed = [ui_rows[0][i] if 0 <= i < len(ui_rows[0]) else "<missing column>" for i in mapping]
            log.info("Node %r: first row expected %s", node, expected_rows[0])
            log.info("Node %r: first row actual   %s (expected columns only)", node, narrowed)
        problems = diff_data_explorer_table(expected_headers, expected_rows, ui_headers, ui_rows)
        for problem in problems:
            log.error("Node %r mismatch: %s", node, problem)
        assert not problems, (
            f"Data Explorer node {node!r} mismatch ({len(problems)}):\n"
            + "\n".join(problems)
            + f"\nExpected headers: {expected_headers}\nActual headers:   {ui_headers}"
        )
        log.info(
            "Assert Data Explorer %r table matches expected (%s rows x %s columns)",
            node,
            len(expected_rows),
            len(expected_headers),
        )
