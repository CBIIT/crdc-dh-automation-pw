"""Submission Requests list: navigate and start a new submission request."""

from __future__ import annotations

import logging
import re

from playwright.sync_api import Locator

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.submission_requests_list")

_LIST_CONTAINER = "CRDC/AILocators/SubmissionRequests/List/Container"
_START_BTN = "CRDC/SubmissionRequest/Start_a_SubmissionRequest-Btn"
_STATUS_LBL = "CRDC/AILocators/SubmissionRequests/StatusBar/Status-Lbl"


class SubmissionRequestsListPage(BasePage):
    @property
    def container(self) -> Locator:
        return self._loc(_LIST_CONTAINER)

    def open(self) -> None:
        """Nav bar → Submission Requests; wait for list container."""
        HeaderPage(self.page, self.locators).open_submission_requests()
        self.container.wait_for(state="visible")
        log.info("Submission Requests list open")

    def _start_button(self) -> Locator:
        """Prefer visible label; fall back to legacy MUI id xpath."""
        by_name = self.page.get_by_role(
            "button", name=re.compile(r"Start\s+a\s+Submission\s+Request", re.I)
        )
        if by_name.count() > 0:
            return by_name.first
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
