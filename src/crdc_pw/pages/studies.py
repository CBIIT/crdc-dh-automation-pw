"""Manage Studies list screen.

Tests construct this from hub (StudiesListPage(hub.page, hub.locators)), then:
  open()            — header user menu → Manage Studies
  apply_filters()   — type/select any of study name, program, dbGaP, status, access
  read_table_rows() — current table as lists of cell text

Locator constants are Katalon object-repository paths (YAML), not raw XPath.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Locator, TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.studies")

_CONTAINER = "CRDC/AILocators/Studies/List/Container"
_ADD_STUDY = "CRDC/AILocators/Studies/List/AddStudy-Btn"
_TABLE_ROW = "CRDC/AILocators/GenericTable/TableRow"
_LOADING_ROW = "CRDC/AILocators/GenericTable/LoadingRow"
_STUDY_NAME = "CRDC/AILocators/Studies/List/Filters/StudyName-TxtBx"
_PROGRAM_DDN = "CRDC/AILocators/Studies/List/Filters/Program-Ddn"
_PROGRAM_OPTION = "CRDC/AILocators/Studies/List/Filters/Program-Option"
_DBGAP = "CRDC/AILocators/Studies/List/Filters/DbGaPID-TxtBx"
_STATUS_DDN = "CRDC/AILocators/Studies/List/Filters/Status-Ddn"
_STATUS_OPTION = "CRDC/AILocators/Studies/List/Filters/Status-Option"
_ACCESS_DDN = "CRDC/AILocators/Studies/List/Filters/AccessType-Ddn"
_ACCESS_OPTION = "CRDC/AILocators/Studies/List/Filters/AccessType-Option"


class StudiesListPage(BasePage):
    @property
    def container(self) -> Locator:
        return self._loc(_CONTAINER)

    @property
    def add_study(self) -> Locator:
        return self._loc(_ADD_STUDY)

    def open(self) -> None:
        """Click username → Manage Studies, then wait until the list container is visible."""
        log.info("Navigate: Manage Studies")
        HeaderPage(self.page, self.locators).open_manage_studies()
        self.wait_until_ready()
        log.info("Manage Studies list page loaded")

    def wait_until_ready(self, timeout_ms: int = 30000) -> None:
        """Block until the Manage Studies page container is on screen."""
        self.container.wait_for(state="visible", timeout=timeout_ms)

    def container_visible(self, timeout_ms: int = 10000) -> bool:
        """True if the list container showed up before timeout."""
        return self._is_visible(_CONTAINER, timeout_ms)

    def add_study_visible(self, timeout_ms: int = 5000) -> bool:
        """True if the Add Study button showed up before timeout."""
        return self._is_visible(_ADD_STUDY, timeout_ms)

    def row_count(self) -> int:
        """How many data rows are in the table right now (no wait)."""
        return self._loc(_TABLE_ROW).count()

    def fill_study_name(self, value: str) -> bool:
        """Type into the Study Name filter. False if the box is not there."""
        return self._fill_if_visible(_STUDY_NAME, value)

    def fill_dbgap(self, value: str) -> bool:
        """Type into the dbGaP ID filter. False if the box is not there."""
        return self._fill_if_visible(_DBGAP, value)

    def select_program(self, program: str) -> bool:
        """Open the Program dropdown and click that option."""
        return self._select_dropdown(_PROGRAM_DDN, _PROGRAM_OPTION, program=program)

    def select_status(self, status: str) -> bool:
        """Open the Status dropdown and click that option."""
        return self._select_dropdown(_STATUS_DDN, _STATUS_OPTION, status=status)

    def select_access_type(self, access_type: str) -> bool:
        """Open the Access Type dropdown and click that option."""
        return self._select_dropdown(_ACCESS_DDN, _ACCESS_OPTION, accessType=access_type)

    def apply_filters(
        self,
        study_name: str | None = None,
        program: str | None = None,
        dbgap: str | None = None,
        status: str | None = None,
        access_type: str | None = None,
    ) -> None:
        """Fill/select only the filters that have a value, then wait for the table to reload.

        Blank or None arguments are skipped, same as Katalon applyManageStudiesFilters.
        """
        study_name = _trim(study_name)
        program = _trim(program)
        dbgap = _trim(dbgap)
        status = _trim(status)
        access_type = _trim(access_type)
        if not any((study_name, program, dbgap, status, access_type)):
            log.info("Apply Manage Studies filters: no criteria; skipping")
            return
        log.info(
            "Apply Manage Studies filters: studyName=%r program=%r dbGaP=%r status=%r accessType=%r",
            study_name,
            program,
            dbgap,
            status,
            access_type,
        )
        if study_name:
            self.fill_study_name(study_name)
        if program:
            self.select_program(program)
        if dbgap:
            self.fill_dbgap(dbgap)
        if status:
            self.select_status(status)
        if access_type:
            self.select_access_type(access_type)
        self.wait_for_table_settled()
        log.info("Apply Manage Studies filters: completed")

    def wait_for_table_settled(self, timeout_ms: int = 15000) -> None:
        """Wait until the table spinner/loading row is gone. No-op if it never appeared."""
        try:
            self._loc(_LOADING_ROW).first.wait_for(state="hidden", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            pass

    def read_table_rows(self) -> list[list[str]]:
        """Each visible data row as a list of td text (header order). Empty list if none."""
        self.wait_for_table_settled()
        rows: list[list[str]] = []
        for row in self._loc(_TABLE_ROW).all():
            cells = [text.strip() for text in row.locator("td").all_inner_texts()]
            rows.append(cells)
        return rows

    def _is_visible(self, path: str, timeout_ms: int) -> bool:
        try:
            self._loc(path).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    def _fill_if_visible(self, path: str, value: str, timeout_ms: int = 5000) -> bool:
        """Type into a text filter only if that field is on screen."""
        if not self._is_visible(path, timeout_ms):
            return False
        box = self._loc(path).first
        box.fill(value)
        return True

    def _select_dropdown(
        self, dropdown_path: str, option_path: str, timeout_ms: int = 5000, **placeholders: str
    ) -> bool:
        """Click a MUI/select dropdown, then the option whose YAML path uses placeholders."""
        if not self._is_visible(dropdown_path, timeout_ms):
            return False
        self._loc(dropdown_path).first.click()
        option = self._loc(option_path, **placeholders).first
        option.wait_for(state="visible", timeout=timeout_ms)
        option.click()
        return True


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
