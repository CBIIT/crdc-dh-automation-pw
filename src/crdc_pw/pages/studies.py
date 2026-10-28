"""Manage Studies list screen.

Tests construct this from hub (StudiesListPage(hub.page, hub.locators)), then:
  open()            — header user menu → Manage Studies
  apply_filters()   — type/select any of study name, program, dbGaP, status, access
  read_table_rows() — current table as lists of cell text

YAML paths stay on this page. Tests use studies.container / studies.add_study.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Locator

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

    def wait_until_ready(self) -> None:
        """Block until the Manage Studies page container is on screen (Hub default timeout)."""
        self.container.wait_for(state="visible")

    def row_count(self) -> int:
        """How many data rows are in the table right now (no wait)."""
        return self._loc(_TABLE_ROW).count()

    def fill_study_name(self, value: str) -> None:
        """Type into the Study Name filter. Fails if the box is not there."""
        self._loc(_STUDY_NAME).first.fill(value)

    def fill_dbgap(self, value: str) -> None:
        """Type into the dbGaP ID filter. Fails if the box is not there."""
        self._loc(_DBGAP).first.fill(value)

    def select_program(self, program: str) -> None:
        """Open the Program dropdown and click that option."""
        self._select_dropdown(self._loc(_PROGRAM_DDN), self._loc(_PROGRAM_OPTION, program=program))

    def select_status(self, status: str) -> None:
        """Open the Status dropdown and click that option."""
        self._select_dropdown(self._loc(_STATUS_DDN), self._loc(_STATUS_OPTION, status=status))

    def select_access_type(self, access_type: str) -> None:
        """Open the Access Type dropdown and click that option."""
        self._select_dropdown(
            self._loc(_ACCESS_DDN), self._loc(_ACCESS_OPTION, accessType=access_type)
        )

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
        study_name = self._trim(study_name)
        program = self._trim(program)
        dbgap = self._trim(dbgap)
        status = self._trim(status)
        access_type = self._trim(access_type)
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
        rows = self._loc(_TABLE_ROW)
        before = self._table_fingerprint(rows)
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
        self._wait_for_table_settled(self._loc(_LOADING_ROW), rows, previous=before)
        log.info("Apply Manage Studies filters: completed")

    def wait_for_table_settled(self) -> None:
        """Wait until the table spinner is gone. Used after open when no filter ran."""
        self._wait_for_table_settled(self._loc(_LOADING_ROW))

    def read_table_rows(self) -> list[list[str]]:
        """Each visible data row as a list of td text (header order). Empty list if none."""
        self.wait_for_table_settled()
        return self._read_table_rows(self._loc(_TABLE_ROW))
