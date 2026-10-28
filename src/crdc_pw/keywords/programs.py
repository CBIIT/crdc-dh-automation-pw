"""Manage Programs list. Katalon utilities.ManagePrograms (navigate, list, filters)."""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from crdc_pw.locators.loader import LocatorLoader
from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.programs import ProgramsListPage

log = logging.getLogger("crdc_pw.programs")


class ManageProgramsKeywords:
    def __init__(self, page: Page, locators: LocatorLoader) -> None:
        self.header = HeaderPage(page, locators)
        self.list_page = ProgramsListPage(page, locators)

    def navigate_to_manage_programs(self) -> None:
        """Open Manage Programs from the header and wait for the list container."""
        log.info("Navigate: Manage Programs")
        self.header.open_manage_programs()
        self.list_page.wait_until_ready()
        log.info("Manage Programs list page loaded")

    def verify_list_page(self) -> None:
        """Container and Add Program are present. Row count is logged; 0 is allowed."""
        assert self.list_page.container_visible(), "Manage Programs list container not found"
        assert self.list_page.add_program_visible(), "Add Program button not found"
        self.list_page.wait_for_table_settled()
        rows = self.list_page.row_count()
        log.info("Assert Manage Programs: container and Add Program visible (rows=%s)", rows)

    def apply_filters(
        self,
        program_name: str | None = None,
        study_name: str | None = None,
    ) -> None:
        """Apply list filters. Blank values are skipped, same as Katalon applyManageProgramsFilters."""
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
            self.list_page.fill_program_name(program_name)
        if study_name:
            self.list_page.fill_study_name(study_name)
        self.list_page.wait_for_table_settled()
        log.info("Apply Manage Programs filters: completed")

    def read_table_rows(self) -> list[list[str]]:
        """Current table rows as lists of cell text. Katalon readManageProgramsTableRows."""
        rows = self.list_page.read_table_rows()
        log.info("Manage Programs table row count: %s", len(rows))
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
            log.info("Assert Manage Programs: row count >= %s (actual=%s)", expect_at_least_rows, count)

        needle = _trim(row_contains)
        if needle:
            found = any(needle in (cell or "") for row in rows for cell in row)
            assert found, f"no row contains {needle!r}"
            log.info("Assert Manage Programs: a row contains %r", needle)

        log.info("Assert Manage Programs filter results: completed; rows=%s", count)


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
