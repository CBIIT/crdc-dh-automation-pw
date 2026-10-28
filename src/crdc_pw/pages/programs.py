"""Manage Programs list screen.

Tests construct this from hub (ProgramsListPage(hub.page, hub.locators)), then:
  open()            — header user menu → Manage Programs
  apply_filters()   — type program name and/or study name
  read_table_rows() — current table as lists of cell text

Locator constants are Katalon object-repository paths (YAML), not raw XPath.
"""

from __future__ import annotations

import logging

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.programs")

CONTAINER = "CRDC/AILocators/Programs/List/Container"
ADD_PROGRAM = "CRDC/AILocators/Programs/List/AddProgram-Btn"
TABLE_ROW = "CRDC/AILocators/GenericTable/TableRow"
LOADING_ROW = "CRDC/AILocators/GenericTable/LoadingRow"
PROGRAM_NAME = "CRDC/AILocators/Programs/List/Filters/ProgramName-TxtBx"
STUDY_NAME = "CRDC/AILocators/Programs/List/Filters/StudyName-TxtBx"


class ProgramsListPage(BasePage):
    def open(self) -> None:
        """Click username → Manage Programs, then wait until the list container is visible."""
        log.info("Navigate: Manage Programs")
        HeaderPage(self.page, self.locators).open_manage_programs()
        self.wait_until_ready()
        log.info("Manage Programs list page loaded")

    def wait_until_ready(self, timeout_ms: int = 30000) -> None:
        """Block until the Manage Programs page container is on screen."""
        self.loc(CONTAINER).wait_for(state="visible", timeout=timeout_ms)

    def container_visible(self, timeout_ms: int = 10000) -> bool:
        """True if the list container showed up before timeout."""
        return self._is_visible(CONTAINER, timeout_ms)

    def add_program_visible(self, timeout_ms: int = 5000) -> bool:
        """True if the Add Program button showed up before timeout."""
        return self._is_visible(ADD_PROGRAM, timeout_ms)

    def row_count(self) -> int:
        """How many data rows are in the table right now (no wait)."""
        return self.loc(TABLE_ROW).count()

    def fill_program_name(self, value: str) -> bool:
        """Type into the Program Name filter. False if the box is not there."""
        return self._fill_if_visible(PROGRAM_NAME, value)

    def fill_study_name(self, value: str) -> bool:
        """Type into the Study Name filter. False if the box is not there."""
        return self._fill_if_visible(STUDY_NAME, value)

    def apply_filters(
        self,
        program_name: str | None = None,
        study_name: str | None = None,
    ) -> None:
        """Fill only the filters that have a value, then wait for the table to reload.

        Blank or None arguments are skipped, same as Katalon applyManageProgramsFilters.
        """
        program_name = _trim(program_name)
        study_name = _trim(study_name)
        if not any((program_name, study_name)):
            log.info("Apply Manage Programs filters: no criteria; skipping")
            return
        log.info(
            "Apply Manage Programs filters: programName=%r studyName=%r",
            program_name,
            study_name,
        )
        if program_name:
            self.fill_program_name(program_name)
        if study_name:
            self.fill_study_name(study_name)
        self.wait_for_table_settled()
        log.info("Apply Manage Programs filters: completed")

    def wait_for_table_settled(self, timeout_ms: int = 15000) -> None:
        """Wait until the table spinner/loading row is gone. No-op if it never appeared."""
        try:
            self.loc(LOADING_ROW).first.wait_for(state="hidden", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            pass

    def read_table_rows(self) -> list[list[str]]:
        """Each visible data row as a list of td text (header order). Empty list if none."""
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
        """Type into a text filter only if that field is on screen."""
        if not self._is_visible(path, timeout_ms):
            return False
        box = self.loc(path).first
        box.fill(value)
        return True


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
