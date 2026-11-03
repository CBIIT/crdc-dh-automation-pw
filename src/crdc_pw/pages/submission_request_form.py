"""Submission Request questionnaire form (status bar, Save, import/export)."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from playwright.sync_api import Locator

from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.base import BasePage
from crdc_pw.submission_request.constants import (
    SR_SAVE_DISABLED_TOOLTIP,
    SR_SAVE_DISABLED_TOOLTIP_SUBSTRING,
)
from crdc_pw.utils.ui_helpers import (
    assert_button_enabled,
    verify_tooltip_on_hover,
    wait_for_button_stable,
)

log = logging.getLogger("crdc_pw.submission_request_form")

_STATUS_LBL = "CRDC/AILocators/SubmissionRequests/StatusBar/Status-Lbl"
_SAVE_BTN = "CRDC/AILocators/SubmissionRequests/Form/Navigation/Save-Btn"
_SAVE_TOOLTIP = "CRDC/AILocators/SubmissionRequests/Form/Navigation/Save-Btn-TooltipTrigger"
_PI_ADDRESS = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-Address-TxtBx"
_EXPORT_BTN = "CRDC/AILocators/SubmissionRequests/Form/ExportForm/ExportForm-Btn"
_IMPORT_BTN = "CRDC/AILocators/SubmissionRequests/Form/ImportForm/ImportForm-Btn"
_IMPORT_UPLOAD = "CRDC/AILocators/SubmissionRequests/Form/ImportDialog/Upload-Input"
_IMPORT_CONFIRM = "CRDC/AILocators/SubmissionRequests/Form/ImportDialog/Confirm-Btn"
_SNACKBAR = "CRDC/AILocators/Global/Notistack-Snackbar"

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
