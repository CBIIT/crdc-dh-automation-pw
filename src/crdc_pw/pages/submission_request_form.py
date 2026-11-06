"""Submission Request questionnaire: UI chrome, section fill, and cross-screen keywords.

List screen actions live on SubmissionRequestsListPage; methods here that need the
list (inquire, open by study) call SubmissionRequestsListPage(self._hub) internally
(Katalon utilities.SubmissionRequest parity).
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Locator

from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.base import BasePage
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage
from crdc_pw.utils.submission_request_excel import get_sheet_row
from crdc_pw.utils.ui_helpers import (
    assert_button_enabled,
    verify_tooltip_on_hover_page,
    wait_for_button_stable,
)

log = logging.getLogger("crdc_pw.submission_request_form")

# CRDCDH-3948 — aligned with utilities.SubmissionRequest (Katalon)
SR_SAVE_DISABLED_TOOLTIP = (
    "No changes have been made. Please make edits to the form then click save."
)
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

# CRDCDH-3952 — Section D date field tooltips (Jira CRDCDH-3952 / FE CRDCDH-3978)
SR_SECTION_D_TARGETED_DELIVERY_TOOLTIP = (
    "The date that transfer of data from the submitter to CRDC Submission Portal is "
    "expected to begin."
)
SR_SECTION_D_EXPECTED_PUB_TOOLTIP = (
    "The date that submitters expect any paper using this data will be published."
)

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
_PROGRESS_D = "CRDC/AILocators/SubmissionRequests/Form/Review/ProgressBar-SectionD"
_SECTION_D_TARGETED_DELIVERY = (
    "CRDC/AILocators/SubmissionRequests/Form/SectionD/TargetedDeliveryDate-TxtBx"
)
_PROGRESS_REVIEW = "CRDC/AILocators/SubmissionRequests/Form/Review/ProgressBar-Review"
_INQUIRE_BTN = "CRDC/AILocators/SubmissionRequests/Form/Navigation/Inquire-Btn"
_APPROVE_BTN = "CRDC/AILocators/SubmissionRequests/Form/Navigation/Approve-Btn"
_REJECT_BTN = "CRDC/AILocators/SubmissionRequests/Form/Navigation/Reject-Btn"
_INQUIRE_COMMENT = "CRDC/AILocators/SubmissionRequests/InquireDialog/ReviewComment-TxtBx"
_INQUIRE_CONFIRM = "CRDC/AILocators/SubmissionRequests/InquireDialog/ConfirmInquire-Btn"
_APPROVE_COMMENT = "CRDC/AILocators/SubmissionRequests/ApproveDialog/ReviewComment-TxtBx"
_APPROVE_CONFIRM = "CRDC/AILocators/SubmissionRequests/ApproveDialog/ConfirmApprove-Btn"

# Section A–D fill (Katalon enter* keywords)
_A_PI_FN = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-FirstName-TxtBx"
_A_PI_LN = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-LastName-TxtBx"
_A_PI_POS = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-Position-TxtBx"
_A_PI_EMAIL = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-Email-TxtBx"
_A_PI_INST = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-Institution-Ddn"
_A_PI_ADDR = _PI_ADDRESS
_A_PC_FN = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-FirstName-TxtBx"
_A_PC_LN = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-LastName-TxtBx"
_A_PC_POS = _PC_POSITION
_A_PC_EMAIL = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-Email-TxtBx"
_A_PC_INST = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-Institution-Ddn"
_A_PC_PHONE = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-Phone-TxtBx"
_B_PROGRAM = "CRDC/AILocators/SubmissionRequests/Form/SectionB/Program-Ddn"
_B_PROG_TITLE = "CRDC/AILocators/SubmissionRequests/Form/SectionB/ProgramTitle-TxtBx"
_B_PROG_ABBR = "CRDC/AILocators/SubmissionRequests/Form/SectionB/ProgramAbbreviation-TxtBx"
_B_PROG_DESC = "CRDC/AILocators/SubmissionRequests/Form/SectionB/ProgramDescription-TxtBx"
_B_STUDY_TITLE = "CRDC/AILocators/SubmissionRequests/Form/SectionB/StudyTitle-TxtBx"
_B_STUDY_ABBR = "CRDC/AILocators/SubmissionRequests/Form/SectionB/StudyAbbreviation-TxtBx"
_B_STUDY_DESC = "CRDC/AILocators/SubmissionRequests/Form/SectionB/StudyDescription-TxtBx"
_B_FUND_AGENCY = "CRDC/SubmissionRequest/Section-B/FundingAgency-Dd"
_B_GRANT = "CRDC/SubmissionRequest/Section-B/GrantContractNumber-Txtbx"
_B_NCI_OFF = "CRDC/SubmissionRequest/Section-B/NCIProgramOfficer-Txtbx"
_C_OPEN = "CRDC/SubmissionRequest/Section-C/OpenAccess-ChkBx"
_C_CONTROLLED = "CRDC/SubmissionRequest/Section-C/ControlledAccess-Chkbx"
_C_DBGAP = "CRDC/SubmissionRequest/Section-C/dbGapRegistered-TogleBtn"
_C_DBGAP_PHS = "CRDC/SubmissionRequest/Section-C/dbGapPHSNumber-Txtbx"
_C_CANCER = "CRDC/SubmissionRequest/Section-C/CancerTypes-Dd"
_C_PRE_CANCER = "CRDC/SubmissionRequest/Section-C/PreCancerTypes-Txtbx"
_C_SPECIES = "CRDC/SubmissionRequest/Section-C/SpeciesOfSubjects-Dd"
_C_NUM_SUBJ = "CRDC/SubmissionRequest/Section-C/NumOfSubjectsIncludInSub-Txtbx"
_D_TARGET_DATE = "CRDC/SubmissionRequest/Section-D/TragetSubmDelivryDate-TxtBx"
_D_PUB_DATE = "CRDC/SubmissionRequest/Section-D/ExpctdPublicationDate-TxtBx"
_D_FILE_TYPE = "CRDC/SubmissionRequest/Section-D/FileType-RowOne-Dd"
_D_FILE_EXT = "CRDC/SubmissionRequest/Section-D/FileExtension-RowOne-Dd"
_D_NUM_FILES = "CRDC/SubmissionRequest/Section-D/NumOfFiles-RowOne-Txtbx"
_D_DATA_SIZE = "CRDC/SubmissionRequest/Section-D/EstimDtaSiz-RowOne-Txtbx"
_D_DEID_YES = "CRDC/SubmissionRequest/Section-D/ConfirmDataIdentified_yes-RdoBtn"
_D_COMMENT = "CRDC/SubmissionRequest/Section-D/AdditionalComnt-TxtBx"
_DD_VALUE = "CRDC/SubmissionRequest/CrdcDdValue"
_TOGGLE = "CRDC/SubmissionRequest/Toggle-Btn"

_DOWNLOAD_DIR = repo_root() / "test-results" / "downloads"


def _stamp() -> str:
    """Unique suffix for study/program names (Katalon M-d-yyyy-HH-mm plus seconds)."""
    now = datetime.now()
    return (
        f"{now.month}-{now.day}-{now.year}-"
        f"{now.hour:02d}-{now.minute:02d}-{now.second:02d}"
    )


def _s(value: Any) -> str:
    """Normalize Excel cell value to stripped string."""
    if value is None:
        return ""
    return str(value).strip()


def _xpath_literal(text: str) -> str:
    """XPath string literal for dynamic checkbox id contains() lookups."""
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    parts = text.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"


def _field_label(yaml_path: str) -> str:
    """Short locator name for log lines (last segment of Katalon path)."""
    return yaml_path.rsplit("/", 1)[-1]


class SubmissionRequestFormPage(BasePage):
    """SR form page — read top-to-bottom in four layers:

    1. Form UI — locators, status/Save asserts, navigation, review dialogs, import/export.
    2. Section fill — Katalon enter_* / select_* (Excel-driven fields on this screen).
    3. Orchestration — fill_submission_request_all_sections (A–D with Save/Next).
    4. Cross-screen workflows — list + form keywords (inquire, approve, open by study).
    """

    last_entered_study_title: str | None = None
    last_entered_study_abbreviation: str | None = None
    last_entered_program_name: str | None = None

    # -------------------------------------------------------------------------
    # Form UI — status bar, navigation, field edits, import/export, review
    # -------------------------------------------------------------------------

    @property
    def save_button(self) -> Locator:
        """Sidebar Save button."""
        return self._loc(_SAVE_BTN)

    @property
    def status_label(self) -> Locator:
        """Status bar label (NEW, IN PROGRESS, IN REVISION, …)."""
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
        """Poll until Save enabled/disabled state is stable (Katalon waitUntilStableForButton)."""
        wait_for_button_stable(self.save_button, enabled=enabled, timeout_s=timeout_s)

    def assert_save_disabled(self) -> None:
        """Assert Save is disabled after state stabilizes."""
        self.wait_save_stable(enabled=False)
        assert_button_enabled(self.save_button, False)

    def assert_save_enabled(self) -> None:
        """Assert Save is enabled after state stabilizes."""
        self.wait_save_stable(enabled=True)
        assert_button_enabled(self.save_button, True)

    def assert_save_disabled_tooltip(self) -> None:
        """Hover Save wrapper and assert the no-changes disabled tooltip (CRDCDH-3948)."""
        verify_tooltip_on_hover_page(
            self,
            self._loc(_SAVE_TOOLTIP),
            SR_SAVE_DISABLED_TOOLTIP,
        )
        log.info("Save disabled tooltip verified")

    def set_pi_address(self, text: str) -> None:
        """Set Section A PI address (used to dirty the form in 3948 tests)."""
        field = self._loc(_PI_ADDRESS).first
        field.click()
        field.fill(text)
        log.info("PI address set")

    def set_primary_contact_position(self, text: str) -> None:
        """Set Section A primary contact position (editable on Reopened SR)."""
        field = self._loc(_PC_POSITION).first
        field.click()
        field.fill(text)
        log.info("Primary contact position set")

    def click_progress_bar_section_a(self) -> None:
        """Jump to Section A via the progress bar."""
        self._loc(_PROGRESS_A).first.click()
        log.info("Opened Section A via progress bar")

    def click_progress_bar_section_d(self) -> None:
        """Jump to Section D and wait for the targeted delivery date field."""
        self._loc(_PROGRESS_D).first.click()
        self._loc(_SECTION_D_TARGETED_DELIVERY).first.wait_for(state="visible", timeout=30_000)
        log.info("Opened Section D via progress bar")

    def click_next(self) -> None:
        """Click Next to advance to the following questionnaire section."""
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
        """Open Inquire or Approve, enter review comment, and confirm the dialog."""
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
        """Open the Review section from the progress bar (Fed Lead on Review screen)."""
        bar = self._loc(_PROGRESS_REVIEW).first
        bar.wait_for(state="visible", timeout=45_000)
        bar.click()
        self.page.wait_for_timeout(2000)
        log.info("Opened Review section via progress bar")

    def is_submit_button_visible(self, *, timeout_ms: int = 40_000) -> bool:
        """True when Submit is visible on the questionnaire (PBAC submission_request:submit)."""
        btn = self._loc(_SUBMIT_BTN).first
        try:
            btn.wait_for(state="visible", timeout=timeout_ms)
        except Exception:
            return False
        return btn.is_visible()

    def are_review_decision_buttons_visible(self) -> bool:
        """True when Approve, Reject, and Inquire are visible (PBAC submission_request:review)."""
        approve = self._loc(_APPROVE_BTN).first
        reject = self._loc(_REJECT_BTN).first
        inquire = self._loc(_INQUIRE_BTN).first
        return approve.is_visible() and reject.is_visible() and inquire.is_visible()

    def inquire_with_comment(self, comment: str = _DEFAULT_INQUIRE_COMMENT) -> None:
        """Fed Lead: Inquire with comment (form must be on Review with Inquire visible)."""
        self._confirm_review_decision(
            _INQUIRE_BTN, _INQUIRE_COMMENT, _INQUIRE_CONFIRM, comment
        )

    def approve_with_comment(self, comment: str = _DEFAULT_APPROVAL_COMMENT) -> None:
        """Fed Lead: Approve with comment (form must be on Review with Approve visible)."""
        self._confirm_review_decision(
            _APPROVE_BTN, _APPROVE_COMMENT, _APPROVE_CONFIRM, comment
        )

    def click_save(self) -> None:
        """Click Save without waiting for side effects."""
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
        """Import Form dialog: upload .xlsx and confirm (Katalon importSubmissionRequestExcel)."""
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

    # -------------------------------------------------------------------------
    # Section fill — helpers and Katalon enter_* / select_* (this screen only)
    # -------------------------------------------------------------------------

    def _fill_if_empty(self, path: str, value: str) -> None:
        """Fill text field only when empty (PI fields on partial forms)."""
        field = self._loc(path).first
        field.wait_for(state="visible", timeout=20_000)
        existing = field.input_value()
        if existing and existing.strip():
            log.info("SR fill skip (already set): %s", _field_label(path))
            return
        log.info("SR fill: %s", _field_label(path))
        field.fill(_s(value))

    def _fill(self, path: str, value: str) -> None:
        """Click and fill a text field with the given value."""
        log.info("SR fill: %s", _field_label(path))
        field = self._loc(path).first
        field.wait_for(state="visible", timeout=20_000)
        field.click()
        field.fill(_s(value))

    def _click_dd_option(self, dd_path: str, option_text: str) -> None:
        """Open CRDC dropdown and select option by visible label."""
        log.info("SR dropdown: %s -> %r", _field_label(dd_path), option_text)
        self._loc(dd_path).first.click()
        self.page.wait_for_timeout(500)
        xpath = self.locators.get(
            _DD_VALUE, **{"GlobalVariable.CrdcUiElement": option_text}
        )
        opt = self.page.locator(xpath).first
        opt.scroll_into_view_if_needed()
        opt.click()

    def enter_principal_investigator_info(self, data_row_num: int) -> None:
        """Section A PI fields from SubmissionRequest.xlsx section-a row."""
        log.info("SR Section A: principal investigator (excel row %s)", data_row_num)
        row = get_sheet_row("section-a", data_row_num)
        mapping = [
            (_A_PI_FN, "pi-first-name"),
            (_A_PI_LN, "pi-last-name"),
            (_A_PI_POS, "position"),
            (_A_PI_EMAIL, "pi-email"),
            (_A_PI_INST, "pi-institution"),
            (_A_PI_ADDR, "pi-instit-address"),
        ]
        for path, key in mapping:
            field = self._loc(path).first
            field.wait_for(state="visible", timeout=20_000)
            new_val = _s(row.get(key))
            if key == "pi-email":
                log.info("SR fill: %s", _field_label(path))
                field.click()
                field.fill(new_val)
            else:
                self._fill_if_empty(path, new_val)

    def enter_primary_contact_info(self, data_row_num: int) -> None:
        """Section A primary contact from section-a row."""
        log.info("SR Section A: primary contact (excel row %s)", data_row_num)
        row = get_sheet_row("section-a", data_row_num)
        for path, key in [
            (_A_PC_FN, "pc-first-name"),
            (_A_PC_LN, "pc-last-name"),
            (_A_PC_POS, "pc-position"),
            (_A_PC_EMAIL, "pc-email"),
            (_A_PC_INST, "pc-institution"),
            (_A_PC_PHONE, "pc-phone"),
        ]:
            self._fill(path, _s(row.get(key)))

    def enter_program_info(self, dd_value: str, data_row_num: int) -> None:
        """Section B program dropdown and optional Other program fields with timestamp suffix."""
        log.info("SR Section B: program %r (excel row %s)", dd_value, data_row_num)
        row = get_sheet_row("section-b", data_row_num)
        ts = _stamp()
        self._click_dd_option(_B_PROGRAM, dd_value)
        if "Other" in dd_value:
            base_title = _s(row.get("program-title"))
            SubmissionRequestFormPage.last_entered_program_name = base_title + ts
            self._fill(_B_PROG_TITLE, SubmissionRequestFormPage.last_entered_program_name)
            self._fill(_B_PROG_ABBR, _s(row.get("prog-abbreviation")) + ts)
            self._fill(_B_PROG_DESC, _s(row.get("prog-description")))
        elif any(x in dd_value for x in ("CCDI", "CPTAC", "DCCPS", "HTAN")):
            SubmissionRequestFormPage.last_entered_program_name = None
        else:
            raise ValueError(f"Unsupported program dropdown value: {dd_value!r}")

    def enter_study_info(self, data_row_num: int) -> None:
        """Section B study title/abbrev/description; sets last_entered_study_* class attrs."""
        log.info("SR Section B: study info (excel row %s)", data_row_num)
        row = get_sheet_row("section-b", data_row_num)
        ts = _stamp()
        title = _s(row.get("study-title")) + ts
        abbrev = _s(row.get("study-abbreviation")) + ts
        log.info("SR Section B: study title %r", title)
        SubmissionRequestFormPage.last_entered_study_title = title
        SubmissionRequestFormPage.last_entered_study_abbreviation = abbrev
        self._fill(_B_STUDY_TITLE, title)
        self._fill(_B_STUDY_ABBR, abbrev)
        self._fill(_B_STUDY_DESC, _s(row.get("study-description")))

    def enter_funding_agency_info(self, data_row_num: int) -> None:
        """Section B funding agency, grant, and NCI program officer from section-b row."""
        log.info("SR Section B: funding agency (excel row %s)", data_row_num)
        row = get_sheet_row("section-b", data_row_num)
        self._fill(_B_FUND_AGENCY, _s(row.get("funding-agency")))
        self._fill(_B_GRANT, _s(row.get("grant-number")))
        self._fill(_B_NCI_OFF, _s(row.get("nci-prog-officer")))

    def enter_data_access_type_and_dbgap_reg_info(
        self, access_type: str, db_gap_registered: str
    ) -> None:
        """Section C open/controlled/both access and optional dbGaP registration."""
        log.info(
            "SR Section C: data access %r dbGaP registered %r",
            access_type,
            db_gap_registered,
        )
        access = access_type.strip().lower()
        if access == "open":
            log.info("SR click: %s", _field_label(_C_OPEN))
            self._loc(_C_OPEN).first.click()
        elif access == "controlled":
            log.info("SR click: %s", _field_label(_C_CONTROLLED))
            self._loc(_C_CONTROLLED).first.click()
        elif access == "both":
            log.info("SR click: %s and %s", _field_label(_C_OPEN), _field_label(_C_CONTROLLED))
            self._loc(_C_OPEN).first.click()
            self._loc(_C_CONTROLLED).first.click()
        else:
            raise ValueError(f"Invalid access type: {access_type!r}")
        if db_gap_registered.strip().lower() == "yes":
            log.info("SR click: %s", _field_label(_C_DBGAP))
            self._loc(_C_DBGAP).first.click()
            self._fill(_C_DBGAP_PHS, "phs005555")

    def enter_cancer_type_and_subjects_info(
        self, cancer_type: str, species_of_subjects: str, data_row_num: int
    ) -> None:
        """Section C cancer type, pre-cancer text, species, and subject count."""
        log.info(
            "SR Section C: cancer %r species %r (excel row %s)",
            cancer_type,
            species_of_subjects,
            data_row_num,
        )
        row = get_sheet_row("section-c", data_row_num)
        self._click_dd_option(_C_CANCER, cancer_type)
        self.page.keyboard.press("Tab")
        self._fill(_C_PRE_CANCER, _s(row.get("pre-cancer-type")))
        self._click_dd_option(_C_SPECIES, species_of_subjects)
        self.page.keyboard.press("Tab")
        self._fill(_C_NUM_SUBJ, _s(row.get("num-of-subjects-included")))

    def enter_target_delivery_and_expected_publication_date(self) -> None:
        """Section D delivery and publication dates using shared future date constant."""
        log.info("SR Section D: targeted delivery and expected publication dates")
        self._fill(_D_TARGET_DATE, SR_QUESTIONNAIRE_FUTURE_DATE)
        self._fill(_D_PUB_DATE, SR_QUESTIONNAIRE_FUTURE_DATE)

    def select_data_types(self, *labels: str) -> None:
        """Section D data type toggles/checkboxes (e.g. genomics, proteomics, imaging)."""
        log.info("SR Section D: data types %s", ", ".join(labels))
        self.page.wait_for_timeout(1000)
        for raw in labels:
            label = raw.lower()
            if "other" in label and label != "other-clinical":
                row = get_sheet_row("section-d", 1)
                self._fill(
                    "CRDC/SubmissionRequest/Section-D/OthrDtaTyp-Txtbx",
                    _s(row.get("other")),
                )
            elif label == "other-clinical":
                row = get_sheet_row("section-d", 1)
                self._fill(
                    "CRDC/SubmissionRequest/Section-D/OthrClinclDtaTyp-Txtbx",
                    _s(row.get("othr-clinicl")),
                )
            elif "imaging" in label:
                log.info("SR Section D: toggle data type %r (imaging + de-id yes)", label)
                xpath = self.locators.get(
                    _TOGGLE, **{"GlobalVariable.CrdcUiElement": label}
                )
                self.page.locator(xpath).first.click()
                self._loc(_D_DEID_YES).first.click()
            else:
                log.info("SR Section D: checkbox data type %r", label)
                toggle = self.page.locator(
                    f"//*[contains(@id,{_xpath_literal(label)}) and @type='checkbox']"
                ).first
                toggle.click()

    def select_file_types(
        self,
        file_type_row: int,
        file_extension_row: int,
        num_of_files_row: int,
        estimated_data_size_row: int,
    ) -> None:
        """Section D first file-type row, de-identified yes, and additional comment from Excel."""
        ft_row = get_sheet_row("section-d", file_type_row)
        fe_row = get_sheet_row("section-d", file_extension_row)
        nf_row = get_sheet_row("section-d", num_of_files_row)
        sz_row = get_sheet_row("section-d", estimated_data_size_row)
        file_type = _s(ft_row.get("file-type"))
        file_ext = _s(fe_row.get("file-extension"))
        log.info(
            "SR Section D: file types row1 type %r extension %r",
            file_type,
            file_ext,
        )
        self._loc(_D_FILE_TYPE).first.scroll_into_view_if_needed()
        self._click_dd_option(_D_FILE_TYPE, file_type)
        self._click_dd_option(_D_FILE_EXT, file_ext)
        self._fill(_D_NUM_FILES, _s(nf_row.get("num-of-file")))
        self._fill(_D_DATA_SIZE, _s(sz_row.get("estimtd-data-size")))
        log.info("SR click: %s", _field_label(_D_DEID_YES))
        self._loc(_D_DEID_YES).first.click()
        comment_row = get_sheet_row("section-d", 1)
        self._fill(_D_COMMENT, _s(comment_row.get("addit-comnt")))

    # -------------------------------------------------------------------------
    # Orchestration — full questionnaire (Katalon fillSubmissionRequestAllSections)
    # -------------------------------------------------------------------------

    def fill_submission_request_all_sections(
        self,
        section_a_row: int,
        program_dd: str,
        program_data_row: int,
        study_data_row: int,
        funding_data_row: int,
        data_access_type: str,
        db_gap_registered: str,
        cancer_type: str,
        species_of_subjects: str,
        section_c_data_row: int,
        first_data_type: str,
        second_data_type: str,
        file_type_row: int,
        file_extension_row: int,
        num_of_files_row: int,
        estimated_data_size_row: int,
    ) -> None:
        """Fill Sections A–D with Save/Next between sections (Katalon fillSubmissionRequestAllSections)."""
        log.info("SR fill: begin Section A (contact)")
        self.enter_principal_investigator_info(section_a_row)
        self.enter_primary_contact_info(section_a_row)
        self.click_save()
        self.click_next()
        self.assert_status("IN PROGRESS")

        log.info("SR fill: begin Section B (program, study, funding)")
        self.enter_program_info(program_dd, program_data_row)
        self.enter_study_info(study_data_row)
        self.enter_funding_agency_info(funding_data_row)
        self.click_save()
        self.click_next()

        log.info("SR fill: begin Section C (data access, cancer, subjects)")
        self.enter_data_access_type_and_dbgap_reg_info(
            data_access_type, db_gap_registered
        )
        self.enter_cancer_type_and_subjects_info(
            cancer_type, species_of_subjects, section_c_data_row
        )
        self.click_save()
        self.click_next()

        log.info("SR fill: begin Section D (dates, data types, file types)")
        self.enter_target_delivery_and_expected_publication_date()
        self.select_data_types(first_data_type, second_data_type)
        self.select_file_types(
            file_type_row,
            file_extension_row,
            num_of_files_row,
            estimated_data_size_row,
        )
        self.click_save()
        self.click_next()
        log.info("SR fill: completed Sections A–D")

    # -------------------------------------------------------------------------
    # Cross-screen workflows — list + form (SubmissionRequestsListPage + self)
    # -------------------------------------------------------------------------

    def _list_page(self) -> SubmissionRequestsListPage:
        """Hub-backed list screen; used only by workflow keywords below."""
        return SubmissionRequestsListPage(self._hub)

    def _open_submission_request_review(self, study_name: str) -> None:
        """Navigate list → Review on row → Review progress bar section."""
        token = (study_name or "").strip()
        if len(token) < 3:
            raise ValueError("study_name must be at least 3 characters")
        sr_list = self._list_page()
        sr_list.open()
        sr_list.apply_submission_requests_list_filters({"study": token})
        self.page.wait_for_timeout(2000)
        sr_list.click_review_for_study_row(token)
        self.click_review_progress_bar()

    def open_submission_request_form_for_study(
        self, study_name: str, list_status: str | None = None
    ) -> None:
        """List filter + Resume/View to open the form for study_name."""
        self._list_page().open_submission_request_form_for_study(study_name, list_status)

    def inquire_submission_request(
        self, study_name: str, inquire_comment: str | None = None
    ) -> None:
        """Fed Lead: filter list, Review row, Review section, Inquire with comment."""
        self._open_submission_request_review(study_name)
        self.inquire_with_comment(
            inquire_comment or _DEFAULT_INQUIRE_COMMENT
        )

    def approve_submission_request(
        self, study_name: str, approval_comment: str | None = None
    ) -> None:
        """Fed Lead: filter list, Review row, Review section, Approve with comment."""
        self._open_submission_request_review(study_name)
        self.approve_with_comment(
            approval_comment or _DEFAULT_APPROVAL_COMMENT
        )

    def reopen_approved_submission_request(self, study_name: str) -> None:
        """Fed Lead: Reopen an Approved SR from the list (does not open the form)."""
        self._list_page().reopen_approved_submission_request(study_name)
