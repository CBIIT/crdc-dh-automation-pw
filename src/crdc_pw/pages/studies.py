"""Manage Studies list screen."""

from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage

CONTAINER = "CRDC/AILocators/Studies/List/Container"
ADD_STUDY = "CRDC/AILocators/Studies/List/AddStudy-Btn"
TABLE_ROW = "CRDC/AILocators/GenericTable/TableRow"
LOADING_ROW = "CRDC/AILocators/GenericTable/LoadingRow"
STUDY_NAME = "CRDC/AILocators/Studies/List/Filters/StudyName-TxtBx"
PROGRAM_DDN = "CRDC/AILocators/Studies/List/Filters/Program-Ddn"
PROGRAM_OPTION = "CRDC/AILocators/Studies/List/Filters/Program-Option"
DBGAP = "CRDC/AILocators/Studies/List/Filters/DbGaPID-TxtBx"
STATUS_DDN = "CRDC/AILocators/Studies/List/Filters/Status-Ddn"
STATUS_OPTION = "CRDC/AILocators/Studies/List/Filters/Status-Option"
ACCESS_DDN = "CRDC/AILocators/Studies/List/Filters/AccessType-Ddn"
ACCESS_OPTION = "CRDC/AILocators/Studies/List/Filters/AccessType-Option"


class StudiesListPage(BasePage):
    def wait_until_ready(self, timeout_ms: int = 30000) -> None:
        self.loc(CONTAINER).wait_for(state="visible", timeout=timeout_ms)

    def container_visible(self, timeout_ms: int = 10000) -> bool:
        return self._is_visible(CONTAINER, timeout_ms)

    def add_study_visible(self, timeout_ms: int = 5000) -> bool:
        return self._is_visible(ADD_STUDY, timeout_ms)

    def row_count(self) -> int:
        return self.loc(TABLE_ROW).count()

    def fill_study_name(self, value: str) -> bool:
        return self._fill_if_visible(STUDY_NAME, value)

    def fill_dbgap(self, value: str) -> bool:
        return self._fill_if_visible(DBGAP, value)

    def select_program(self, program: str) -> bool:
        return self._select_dropdown(PROGRAM_DDN, PROGRAM_OPTION, program=program)

    def select_status(self, status: str) -> bool:
        return self._select_dropdown(STATUS_DDN, STATUS_OPTION, status=status)

    def select_access_type(self, access_type: str) -> bool:
        return self._select_dropdown(ACCESS_DDN, ACCESS_OPTION, accessType=access_type)

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

    def _select_dropdown(self, dropdown_path: str, option_path: str, timeout_ms: int = 5000, **placeholders: str) -> bool:
        if not self._is_visible(dropdown_path, timeout_ms):
            return False
        self.loc(dropdown_path).first.click()
        option = self.loc(option_path, **placeholders).first
        option.wait_for(state="visible", timeout=timeout_ms)
        option.click()
        return True
