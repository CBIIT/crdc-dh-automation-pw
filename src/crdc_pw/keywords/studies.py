"""Manage Studies list. Katalon utilities.ManageStudies (navigate, list, filters)."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from crdc_pw.locators.loader import LocatorLoader
from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.studies import StudiesListPage

log = logging.getLogger("crdc_pw.studies")


class ManageStudiesKeywords:
    def __init__(self, page: Page, locators: LocatorLoader) -> None:
        self.header = HeaderPage(page, locators)
        self.list_page = StudiesListPage(page, locators)

    def navigate_to_manage_studies(self) -> None:
        """Open Manage Studies from the header and wait for the list container."""
        log.info("Navigate: Manage Studies")
        self.header.open_manage_studies()
        self.list_page.wait_until_ready()
        log.info("Manage Studies list page loaded")

    def verify_list_page(self) -> None:
        """Container and Add Study are present. Row count is logged; 0 is allowed."""
        assert self.list_page.container_visible(), "Manage Studies list container not found"
        assert self.list_page.add_study_visible(), "Add Study button not found"
        rows = self.list_page.row_count()
        log.info("Assert Manage Studies: container and Add Study visible (rows=%s)", rows)

    def apply_filters(
        self,
        study_name: str | None = None,
        program: str | None = None,
        dbgap: str | None = None,
        status: str | None = None,
        access_type: str | None = None,
    ) -> None:
        """Apply list filters. Blank values are skipped, same as Katalon applyManageStudiesFilters."""
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
            self.list_page.fill_study_name(study_name)
        if program:
            self.list_page.select_program(program)
        if dbgap:
            self.list_page.fill_dbgap(dbgap)
        if status:
            self.list_page.select_status(status)
        if access_type:
            self.list_page.select_access_type(access_type)
        self.list_page.wait_for_table_settled()
        log.info("Apply Manage Studies filters: completed")

    def read_table_rows(self) -> list[list[str]]:
        """Current table rows as lists of cell text. Katalon readManageStudiesTableRows."""
        rows = self.list_page.read_table_rows()
        log.info("Manage Studies table row count: %s", len(rows))
        return rows

    def verify_filter_results(
        self,
        expect_at_least_rows: int | None = None,
        row_contains: str | None = None,
    ) -> None:
        """Assert min row count and/or that some cell contains the substring."""
        rows = self.read_table_rows()
        count = len(rows)

        if expect_at_least_rows is not None:
            assert count >= expect_at_least_rows, (
                f"expected at least {expect_at_least_rows} rows, got {count}"
            )
            log.info("Assert Manage Studies: row count >= %s (actual=%s)", expect_at_least_rows, count)

        needle = _trim(row_contains)
        if needle:
            found = any(needle in (cell or "") for row in rows for cell in row)
            assert found, f"no row contains {needle!r}"
            log.info("Assert Manage Studies: a row contains %r", needle)

        log.info("Assert Manage Studies filter results: completed; rows=%s", count)


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
