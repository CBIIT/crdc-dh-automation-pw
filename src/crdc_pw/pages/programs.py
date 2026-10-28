"""Manage Programs list screen."""

from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage

CONTAINER = "CRDC/AILocators/Programs/List/Container"
ADD_PROGRAM = "CRDC/AILocators/Programs/List/AddProgram-Btn"
TABLE_ROW = "CRDC/AILocators/GenericTable/TableRow"
LOADING_ROW = "CRDC/AILocators/GenericTable/LoadingRow"
PROGRAM_NAME = "CRDC/AILocators/Programs/List/Filters/ProgramName-TxtBx"
STUDY_NAME = "CRDC/AILocators/Programs/List/Filters/StudyName-TxtBx"


class ProgramsListPage(BasePage):
    def wait_until_ready(self, timeout_ms: int = 30000) -> None:
        self.loc(CONTAINER).wait_for(state="visible", timeout=timeout_ms)

    def container_visible(self, timeout_ms: int = 10000) -> bool:
        return self._is_visible(CONTAINER, timeout_ms)

    def add_program_visible(self, timeout_ms: int = 5000) -> bool:
        return self._is_visible(ADD_PROGRAM, timeout_ms)

    def row_count(self) -> int:
        return self.loc(TABLE_ROW).count()

    def fill_program_name(self, value: str) -> bool:
        return self._fill_if_visible(PROGRAM_NAME, value)

    def fill_study_name(self, value: str) -> bool:
        return self._fill_if_visible(STUDY_NAME, value)

    def wait_for_table_settled(self, timeout_ms: int = 15000) -> None:
        """Wait until the loading row is gone. Katalon used WebUI.delay after filters."""
        try:
            self.loc(LOADING_ROW).first.wait_for(state="hidden", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            pass

    def read_table_rows(self) -> list[list[str]]:
        """Visible table rows as lists of td text, header order. Empty list if none."""
        self.wait_for_table_settled()
        rows: list[list[str]] = []
        for row in self.loc(TABLE_ROW).all():
            cells = [text.strip() for text in row.locator("td").all_inner_texts()]
            rows.append(cells)
        return rows

    def _is_visible(self, path: str, timeout_ms: int) -> bool:
        try:
            self.loc(path).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    def _fill_if_visible(self, path: str, value: str, timeout_ms: int = 5000) -> bool:
        if not self._is_visible(path, timeout_ms):
            return False
        box = self.loc(path).first
        box.fill(value)
        return True
