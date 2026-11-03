"""Submission Request questionnaire form (status bar, Save, import/export)."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from playwright.sync_api import Locator

from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.base import BasePage
from crdc_pw.utils.ui_helpers import (
    assert_button_enabled,
    verify_tooltip_on_hover,
    wait_for_button_stable,
)

log = logging.getLogger("crdc_pw.submission_request_form")

# CRDCDH-3948 — aligned with utilities.SubmissionRequest (Katalon)
SR_SAVE_DISABLED_TOOLTIP = (
    "No changes have been made. Please make edits to the form then click save."
)
SR_SAVE_DISABLED_TOOLTIP_SUBSTRING = "No changes have been made"
SR_IMPORT_NO_CHANGES_MESSAGE = (
    "No changes were applied. The imported file matches the current form."
)
SR_IMPORT_VALIDATION_ERRORS_MESSAGE = (
    "Your data has been imported, but some pages contain validation errors. "
    "Please review each page and resolve before submitting."
)
SR_IMPORT_ALL_PASSED_VALIDATION_MESSAGE = (
    "Your data has been imported and all passed validation. "
    "You may proceed to Review & Submit."
)
SR_IMPORT_VALIDATION_ERRORS_FIXTURE = (
    "InputFiles/CRDC/SubmissionRequest/CRDCDH-3948/"
    "CRDCDH-3948_TC02_import-with-validation-errors.xlsx"
)
SR_QUESTIONNAIRE_FUTURE_DATE = "05/12/2036"

_DEFAULT_INQUIRE_COMMENT = "Automated test inquire - CRDC submission request."
_DEFAULT_APPROVAL_COMMENT = "Automated test approval - CRDC submission request."

_STATUS_LBL = "CRDC/AILocators/SubmissionRequests/StatusBar/Status-Lbl"
_SAVE_BTN = "CRDC/AILocators/SubmissionRequests/Form/Navigation/Save-Btn"
_SAVE_TOOLTIP = "CRDC/AILocators/SubmissionRequests/Form/Navigation/Save-Btn-TooltipTrigger"
_PI_ADDRESS = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-Address-TxtBx"
_EXPORT_BTN = "CRDC/AILocators/SubmissionRequests/Form/ExportForm/ExportForm-Btn"
_IMPORT_BTN = "CRDC/AILocators/SubmissionRequests/Form/ImportForm/ImportForm-Btn"
_IMPORT_UPLOAD = "CRDC/AILocators/SubmissionRequests/Form/ImportDialog/Upload-Input"
_IMPORT_CONFIRM = "CRDC/AILocators/SubmissionRequests/Form/ImportDialog/Confirm-Btn"
_SNACKBAR = "CRDC/AILocators/Global/Notistack-Snackbar"
_NEXT_BTN = "CRDC/AILocators/SubmissionRequests/Form/Navigation/Next-Btn"
_SUBMIT_BTN = "CRDC/SubmissionRequest/Submit-Btn"
_SUBMIT_CONFIRM = "CRDC/SubmissionRequest/PopUpConfirmToSubmit-Btn"
_PC_POSITION = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-Position-TxtBx"
_PROGRESS_A = "CRDC/AILocators/SubmissionRequests/Form/Review/ProgressBar-SectionA"
_PROGRESS_REVIEW = "CRDC/AILocators/SubmissionRequests/Form/Review/ProgressBar-Review"
_INQUIRE_BTN = "CRDC/AILocators/SubmissionRequests/Form/Navigation/Inquire-Btn"
_APPROVE_BTN = "CRDC/AILocators/SubmissionRequests/Form/Navigation/Approve-Btn"
_INQUIRE_COMMENT = "CRDC/AILocators/SubmissionRequests/InquireDialog/ReviewComment-TxtBx"
_INQUIRE_CONFIRM = "CRDC/AILocators/SubmissionRequests/InquireDialog/ConfirmInquire-Btn"
_APPROVE_COMMENT = "CRDC/AILocators/SubmissionRequests/ApproveDialog/ReviewComment-TxtBx"
_APPROVE_CONFIRM = "CRDC/AILocators/SubmissionRequests/ApproveDialog/ConfirmApprove-Btn"

_DOWNLOAD_DIR = repo_root() / "test-results" / "downloads"


class SubmissionRequestFormPage(BasePage):
    @property
    def save_button(self) -> Locator:
        return self._loc(_SAVE_BTN)

    @property
    def status_label(self) -> Locator:
        return self._loc(_STATUS_LBL)

    def assert_status(self, expected: str, *, wait_s: float = 30) -> None:
        """Poll status bar until text matches expected (case-insensitive)."""
        want = expected.strip().upper()
        deadline = time.monotonic() + wait_s
        last = ""
        while time.monotonic() < deadline:
            self.status_label.wait_for(state="visible")
            last = (self.status_label.inner_text() or "").strip().upper()
            if last == want:
                log.info("Status bar: %s", last)
                return
            self.page.wait_for_timeout(400)
        raise AssertionError(
            f"Status bar did not show {want!r} within {wait_s}s (last seen: {last!r})"
        )

    def wait_save_stable(self, *, enabled: bool, timeout_s: float = 30) -> None:
        wait_for_button_stable(self.save_button, enabled=enabled, timeout_s=timeout_s)

    def assert_save_disabled(self) -> None:
        self.wait_save_stable(enabled=False)
        assert_button_enabled(self.save_button, False)

    def assert_save_enabled(self) -> None:
        self.wait_save_stable(enabled=True)
        assert_button_enabled(self.save_button, True)

    def assert_save_disabled_tooltip(self) -> None:
        verify_tooltip_on_hover(
            self.page,
            self._loc(_SAVE_TOOLTIP),
            SR_SAVE_DISABLED_TOOLTIP,
            SR_SAVE_DISABLED_TOOLTIP_SUBSTRING,
        )
        log.info("Save disabled tooltip verified")

    def set_pi_address(self, text: str) -> None:
        field = self._loc(_PI_ADDRESS).first
        field.click()
        field.fill(text)
        log.info("PI address set")

    def set_primary_contact_position(self, text: str) -> None:
        field = self._loc(_PC_POSITION).first
        field.click()
        field.fill(text)
        log.info("Primary contact position set")

    def click_progress_bar_section_a(self) -> None:
        self._loc(_PROGRESS_A).first.click()
        log.info("Opened Section A via progress bar")

    def click_next(self) -> None:
        self._loc(_NEXT_BTN).first.click()
        log.info("Clicked Next")

    def click_submit_button(self) -> None:
        """Submit + confirm; wait until list Start button is back (Katalon clickSubmitButton)."""
        self._loc(_SUBMIT_BTN).first.click()
        self.page.wait_for_timeout(500)
        confirm = self._loc(_SUBMIT_CONFIRM).first
        try:
            confirm.wait_for(state="visible", timeout=5000)
        except Exception:
            confirm = self.page.get_by_role("button", name=re.compile(r"confirm", re.I)).first
        confirm.click()
        self.page.wait_for_timeout(500)
        self.page.get_by_role(
            "button", name=re.compile(r"Start\s+a\s+Submission\s+Request", re.I)
        ).wait_for(state="visible", timeout=40_000)
        log.info("Submitted submission request")

    def _confirm_review_decision(
        self,
        action_path: str,
        comment_path: str,
        confirm_path: str,
        comment: str,
    ) -> None:
        btn = self._loc(action_path).first
        btn.scroll_into_view_if_needed()
        btn.click()
        comment_field = self._loc(comment_path).first
        comment_field.wait_for(state="visible", timeout=10_000)
        comment_field.click()
        # MUI + react-hook-form: fill does not always update state; match Katalon click + sendKeys.
        comment_field.press_sequentially(comment, delay=20)
        confirm = self._loc(confirm_path).first
        confirm.wait_for(state="visible", timeout=10_000)
        confirm.click()
        self.page.wait_for_timeout(2000)
        log.info("Review decision confirmed")

    def click_review_progress_bar(self) -> None:
        bar = self._loc(_PROGRESS_REVIEW).first
        bar.wait_for(state="visible", timeout=45_000)
        bar.click()
        self.page.wait_for_timeout(2000)
        log.info("Opened Review section via progress bar")

    def inquire_with_comment(self, comment: str = _DEFAULT_INQUIRE_COMMENT) -> None:
        self._confirm_review_decision(
            _INQUIRE_BTN, _INQUIRE_COMMENT, _INQUIRE_CONFIRM, comment
        )

    def approve_with_comment(self, comment: str = _DEFAULT_APPROVAL_COMMENT) -> None:
        self._confirm_review_decision(
            _APPROVE_BTN, _APPROVE_COMMENT, _APPROVE_CONFIRM, comment
        )

    def click_save(self) -> None:
        self.save_button.first.click()
        log.info("Clicked Save")

    def export_form_excel(self, *, timeout_s: float = 60) -> Path:
        """Export sidebar Excel; save download under test-results/downloads/."""
        _DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with self.page.expect_download(timeout=timeout_s * 1000) as download_info:
            self._loc(_EXPORT_BTN).first.click()
        download = download_info.value
        suggested = download.suggested_filename or "CRDC_Submission_Request_export.xlsx"
        if not suggested.startswith("CRDC_Submission_Request"):
            log.warning("Unexpected export filename: %s", suggested)
        dest = _DOWNLOAD_DIR / suggested
        download.save_as(dest)
        log.info("Exported SR form: %s", dest)
        return dest

    def import_form_excel(self, path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(path)
        self._loc(_IMPORT_BTN).first.click()
        upload = self._loc(_IMPORT_UPLOAD).first
        upload.wait_for(state="attached", timeout=15_000)
        upload.set_input_files(str(path.resolve()))
        self.page.wait_for_timeout(2000)
        self._loc(_IMPORT_CONFIRM).first.click()
        log.info("Imported SR form from %s", path)

    def assert_snackbar_contains(self, text: str, *, timeout_s: float = 20) -> None:
        """Wait for Notistack message containing text (Katalon verifySubmissionRequestSnackbarError)."""
        expected = text.strip()
        snackbar = self._loc(_SNACKBAR).first
        deadline = time.monotonic() + timeout_s
        visible = ""
        while time.monotonic() < deadline:
            try:
                snackbar.wait_for(state="visible", timeout=2000)
                visible = re.sub(r"\s+", " ", (snackbar.inner_text() or "")).strip()
                if expected in visible:
                    log.info("Snackbar verified: %s", visible[:120])
                    return
            except Exception:
                pass
            self.page.wait_for_timeout(500)
        raise AssertionError(
            f"Snackbar did not contain {expected!r} within {timeout_s}s (last: {visible!r})"
        )
