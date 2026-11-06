"""Submission Requests list: navigate, filter, row actions (Resume/View/Review/Reopen)."""

from __future__ import annotations

import logging
import re
from typing import Mapping

from playwright.sync_api import Locator

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.submission_requests_list")

_LIST_CONTAINER = "CRDC/AILocators/SubmissionRequests/List/Container"
_START_BTN = "CRDC/SubmissionRequest/Start_a_SubmissionRequest-Btn"
_STATUS_LBL = "CRDC/AILocators/SubmissionRequests/StatusBar/Status-Lbl"
_TABLE = "CRDC/AILocators/GenericTable/Table"
_RESET_FILTERS = "CRDC/AILocators/SubmissionRequests/List/Filters/ResetFilters-Btn"
_STUDY_FILTER = "CRDC/AILocators/SubmissionRequests/List/Filters/Study-TxtBx"
_STATUS_FILTER = "CRDC/AILocators/SubmissionRequests/List/Filters/Status-Ddn"
_PROGRAM_FILTER = "CRDC/AILocators/SubmissionRequests/List/Filters/Program-Ddn"
_SUBMITTER_FILTER = "CRDC/AILocators/SubmissionRequests/List/Filters/SubmitterName-TxtBx"
_REOPEN_BTN = "CRDC/AILocators/SubmissionRequests/List/Reopen-Btn"
_DELETE_CONFIRM = "CRDC/AILocators/DeleteDialog/Confirm-Btn"
_DELETE_DIALOG = "CRDC/AILocators/DeleteDialog/Dialog"


class SubmissionRequestsListPage(BasePage):
    """Submission Requests table: filters and per-row Resume/View/Review/Reopen."""

    @property
    def container(self) -> Locator:
        """Main list page wrapper (table and filters)."""
        return self._loc(_LIST_CONTAINER)

    def open(self) -> None:
        """Nav bar → Submission Requests; wait for list container and settled table."""
        HeaderPage(self._hub).open_submission_requests()
        self.container.wait_for(state="visible", timeout=15_000)
        self.wait_for_list_table_settled()
        log.info("Submission Requests list open")

    def wait_for_list_table_settled(self) -> None:
        """Wait until the generic-table loading row is gone (avoid reading placeholder / stale rows)."""
        self.wait_for_generic_table_settled(self._table_rows())

    def _start_button(self) -> Locator:
        """Start a Submission Request on the list — same Katalon repo path as Katalon.

        Uses ``CRDC/SubmissionRequest/Start_a_SubmissionRequest-Btn`` (YAML xpath). Callers that
        need resilience should use ``wait_for(state='visible')`` like ``start_new_submission_request``.
        """
        return self._loc(_START_BTN).first

    def start_new_submission_request(self) -> None:
        """Start SR and accept Read & Accept dialog; wait for form status bar."""
        start = self._start_button()
        start.wait_for(state="visible")
        start.click()
        confirm = self.page.locator("[role='dialog']").locator("#error-dialog-delete-button")
        confirm.wait_for(state="visible", timeout=10_000)
        confirm.click()
        self._loc(_STATUS_LBL).wait_for(state="visible", timeout=40_000)
        log.info("New submission request form ready")

    def reset_submission_requests_filters(self) -> None:
        """Clear list filters when Reset is visible."""
        reset = self._loc(_RESET_FILTERS).first
        if reset.is_visible():
            reset.click()
            self.page.wait_for_timeout(2000)
            log.info("Reset Submission Requests list filters")
            self.wait_for_list_table_settled()

    def apply_submission_requests_list_filters(
        self, criteria: Mapping[str, str] | None
    ) -> None:
        """Apply optional submitterName, program, study, status filters (Katalon list helper)."""
        if not criteria:
            return
        if v := (criteria.get("submitterName") or "").strip():
            field = self._loc(_SUBMITTER_FILTER).first
            if field.is_visible():
                field.fill(v)
                self.page.wait_for_timeout(1000)
        if v := (criteria.get("program") or "").strip():
            self._loc(_PROGRAM_FILTER).first.click()
            self.page.wait_for_timeout(500)
            self.page.locator(f"//li[normalize-space(text())={self._xpath_literal(v)}]").first.click()
            self.page.wait_for_timeout(1000)
        if v := (criteria.get("study") or "").strip():
            field = self._loc(_STUDY_FILTER).first
            field.click()
            field.fill(v)
            self.page.wait_for_timeout(1000)
        if v := (criteria.get("status") or "").strip():
            self._select_status_filter(v)
        self.page.wait_for_timeout(2000)
        self.wait_for_list_table_settled()

    def _select_status_filter(self, status_csv: str) -> None:
        """Multi-select status dropdown; values are comma-separated UI labels."""
        values = [s.strip() for s in status_csv.split(",") if s.strip()]
        if not values:
            return
        self._loc(_STATUS_FILTER).first.click()
        self.page.wait_for_timeout(500)
        listbox = self.page.locator("[role='listbox']").first
        if not listbox.is_visible():
            listbox = self.page.locator("ul.MuiList-root").first
        for _ in range(20):
            selected = listbox.locator("li[aria-selected='true'], li.Mui-selected")
            if selected.count() == 0:
                break
            selected.first.click()
            self.page.wait_for_timeout(200)
        missing: list[str] = []
        for label in values:
            opt = listbox.locator(
                f"xpath=.//li[normalize-space(text())={self._xpath_literal(label)}]"
            )
            if opt.count() == 0:
                missing.append(label)
                continue
            opt.first.click()
            self.page.wait_for_timeout(500)
        if missing:
            raise AssertionError(
                f"Status filter option(s) not found: {missing}. "
                "Use UI labels (Approved, Reopened, In Progress, …)."
            )
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(500)

    @staticmethod
    def _xpath_literal(text: str) -> str:
        """Safe XPath string literal for filter option text."""
        if "'" not in text:
            return f"'{text}'"
        if '"' not in text:
            return f'"{text}"'
        parts = text.split("'")
        return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"

    def _table_rows(self) -> Locator:
        """Data rows in the generic SR list table."""
        return self._loc(_TABLE).locator("tbody tr")

    def open_submission_request_form_for_study(
        self, study_name: str, list_status: str | None = None
    ) -> None:
        """Filter by study (and optional status), then Resume or View the matching row."""
        token = (study_name or "").strip()
        if len(token) < 3:
            raise ValueError("study_name must be at least 3 characters for Study filter")
        self.open()
        self.reset_submission_requests_filters()
        criteria: dict[str, str] = {"study": token}
        if list_status and list_status.strip():
            criteria["status"] = list_status.strip()
        self.apply_submission_requests_list_filters(criteria)
        self._click_resume_or_view_for_study_row(token)
        self._loc(_STATUS_LBL).wait_for(state="visible", timeout=40_000)

    def click_review_for_study_row(self, study_token: str) -> None:
        """Click Review on the row for study_token (caller applies filters first)."""
        self._click_row_action(study_token, action="review")

    def reopen_approved_submission_request(self, study_name: str) -> None:
        """Filter Approved + study, Reopen on the matching row, confirm dialog (stays on list)."""
        token = (study_name or "").strip()
        if len(token) < 3:
            raise ValueError("study_name must be at least 3 characters")
        self.open()
        self.apply_submission_requests_list_filters(
            {"study": token, "status": "Approved"}
        )
        self._click_row_action(token, action="reopen")
        self._loc(_DELETE_DIALOG).wait_for(state="visible", timeout=10_000)
        self._loc(_DELETE_CONFIRM).first.click()
        self._loc(_DELETE_DIALOG).wait_for(state="hidden", timeout=30_000)
        self.page.wait_for_timeout(2000)
        log.info("Reopened approved submission request on list")

    def _click_resume_or_view_for_study_row(self, study_token: str) -> None:
        """Submitter row action: Resume if present, else View."""
        self._click_row_action(study_token, action="resume_or_view")

    def _click_row_action(self, study_token: str, *, action: str) -> None:
        """Find row by study text, single-row fallback, or suffix; click review/resume/view/reopen."""
        rows = self._table_rows()
        count = rows.count()
        if count == 0:
            raise AssertionError("Submission request list: table has no data rows")

        def try_row(row: Locator) -> bool:
            if action == "review":
                btn = row.get_by_role("button", name=re.compile(r"^Review$", re.I))
                if btn.count() == 0:
                    btn = row.locator("xpath=.//button[contains(normalize-space(.), 'Review')]")
            elif action == "resume_or_view":
                btn = row.get_by_role("button", name=re.compile(r"^Resume$", re.I))
                if btn.count() > 0:
                    btn.first.scroll_into_view_if_needed()
                    btn.first.click()
                    return True
                btn = row.get_by_role("button", name=re.compile(r"^View$", re.I))
            elif action == "reopen":
                btn = row.locator("[data-testid='reopen-application-button']")
            else:
                return False
            if btn.count() == 0:
                return False
            btn.first.scroll_into_view_if_needed()
            btn.first.click()
            return True

        for i in range(count):
            row = rows.nth(i)
            text = row.inner_text()
            if study_token in text and try_row(row):
                log.info("List row matched full study token for %s", action)
                return

        actionable: list[int] = []
        for i in range(count):
            row = rows.nth(i)
            if action == "review":
                has = row.get_by_role("button", name=re.compile(r"Review", re.I)).count() > 0
            elif action == "reopen":
                has = row.locator("[data-testid='reopen-application-button']").count() > 0
            else:
                has = (
                    row.get_by_role("button", name=re.compile(r"Resume|View", re.I)).count()
                    > 0
                )
            if has:
                actionable.append(i)
        if len(actionable) == 1 and try_row(rows.nth(actionable[0])):
            log.info("List row: single filtered row for %s", action)
            return

        if len(study_token) > 10:
            tail = study_token[-10:]
            for i in range(count):
                row = rows.nth(i)
                if tail in (row.inner_text() or "") and try_row(row):
                    log.info("List row matched study token suffix for %s", action)
                    return

        raise AssertionError(
            f"Could not find list row action {action!r} for study filter "
            f"({len(actionable)} actionable rows)"
        )
