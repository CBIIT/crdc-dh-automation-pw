"""Manage Programs list screen.

Tests construct this from hub (ProgramsListPage(hub.page, hub.locators)), then:
  open()            — header user menu → Manage Programs
  apply_filters()   — type program name and/or study name
  read_table_rows() — current table as lists of cell text

YAML paths stay on this page. Tests use programs.container / programs.add_program.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Locator

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.programs")

_CONTAINER = "CRDC/AILocators/Programs/List/Container"
_ADD_PROGRAM = "CRDC/AILocators/Programs/List/AddProgram-Btn"
_TABLE_ROW = "CRDC/AILocators/GenericTable/TableRow"
_LOADING_ROW = "CRDC/AILocators/GenericTable/LoadingRow"
_PROGRAM_NAME = "CRDC/AILocators/Programs/List/Filters/ProgramName-TxtBx"
_STUDY_NAME = "CRDC/AILocators/Programs/List/Filters/StudyName-TxtBx"


class ProgramsListPage(BasePage):
    @property
    def container(self) -> Locator:
        return self._loc(_CONTAINER)

    @property
    def add_program(self) -> Locator:
        return self._loc(_ADD_PROGRAM)

    def open(self) -> None:
        """Click username → Manage Programs, then wait until the list container is visible."""
        log.info("Navigate: Manage Programs")
        HeaderPage(self.page, self.locators).open_manage_programs()
        self.wait_until_ready()
        log.info("Manage Programs list page loaded")

    def wait_until_ready(self) -> None:
        """Block until the Manage Programs page container is on screen (Hub default timeout)."""
        self.container.wait_for(state="visible")

    def row_count(self) -> int:
        """How many data rows are in the table right now (no wait)."""
        return self._loc(_TABLE_ROW).count()

    def fill_program_name(self, value: str) -> None:
        """Type into the Program Name filter. Fails if the box is not there."""
        self._loc(_PROGRAM_NAME).first.fill(value)

    def fill_study_name(self, value: str) -> None:
        """Type into the Study Name filter. Fails if the box is not there."""
        self._loc(_STUDY_NAME).first.fill(value)

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
        rows = self._loc(_TABLE_ROW)
        before = self._table_fingerprint(rows)
        if program_name:
            self.fill_program_name(program_name)
        if study_name:
            self.fill_study_name(study_name)
        self._wait_for_table_settled(self._loc(_LOADING_ROW), rows, previous=before)
        log.info("Apply Manage Programs filters: completed")

    def wait_for_table_settled(self) -> None:
        """Wait until the table spinner is gone. Used after open when no filter ran."""
        self._wait_for_table_settled(self._loc(_LOADING_ROW))

    def read_table_rows(self) -> list[list[str]]:
        """Each visible data row as a list of td text (header order). Empty list if none."""
        self.wait_for_table_settled()
        rows: list[list[str]] = []
        for row in self._loc(_TABLE_ROW).all():
            cells = [text.strip() for text in row.locator("td").all_inner_texts()]
            rows.append(cells)
        return rows


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
