"""Data Submission detail: upload, validate, Validation Results, error-details dialog.

Construct DataSubmissionDetailPage(hub) after opening a submission from the list.
TSV oracles stay in utils/validation_results.py.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Mapping

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.base import BasePage
from crdc_pw.utils.validation_results import (
    CrossValidationRow,
    diff_error_details_dialog_issues,
    diff_upload_errors,
    diff_validation_results,
    expected_error_detail_issues_for_row,
    check_export_filename,
    find_expected_validation_results_tsv,
    list_nodes_from_expected_validation_results_folder,
    list_tsv_files_and_nodes_for_tc,
    load_all_expected_error_detail_rows_from_tsv,
    load_expected_upload_errors,
    load_expected_validation_results_tsv,
    load_validation_results_mappings,
    unique_severity_issue_type_pairs_from_expected_tsv,
)

log = logging.getLogger("crdc_pw.data_submission_details")

# QA automation DS create + summary header oracles (Katalon utilities.DataSubmissions static defaults)
DS_AUTOMATION_STUDY_CREATE = "autoQA - AutomationQA_Study"
DS_AUTOMATION_STUDY_CV = "autoQA - AutomationQA_CV"
DS_EXPECTED_STUDY_HEADER = "autoQA"
DS_EXPECTED_PROGRAM = "AUTOPROGRAM"
DS_EXPECTED_SUBMISSION_TYPE_NEW = "New/Update"
DS_EXPECTED_COLLABORATORS_COUNT = "0"
DS_EXPECTED_DATA_CONCIERGE = "pbac.dcp-automation Please Do Not Edit"
DS_COLLABORATORS_TOOLTIP = "Click to add new collaborators or view existing ones."

_SUMMARY_HEADER_LABELS: dict[str, str] = {
    "submission_name": "Submission Name",
    "submitter": "Submitter",
    "submission_type": "Submission Type",
    "collaborators": "Collaborators",
    "study": "Study",
    "data_commons": "Data Commons",
    "program": "Program",
    "data_concierge": "Data Concierge",
}


def normalize_summary_header_value(value: str | None) -> str:
    """Whitespace-normalize summary header text (Katalon compareAndReport)."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


CHOOSE_FILES = "CRDC/DataSubmissions/ChooseFiles-Btn"
UPLOAD_MODEL_VERSION = "CRDC/AILocators/DataSubmissions/Detail/MetadataUpload/ModelVersion-Lbl"
UPLOAD = "CRDC/DataSubmissions/Upload-Btn"
UPLOADING = "CRDC/DataSubmissions/Validation/Uploading-Text"
VALIDATE = "CRDC/DataSubmissions/Validate-Btn"
VR_TAB = "CRDC/DataSubmissions/Validation/ValidationResults-Tab"
VR_EXPANDED = "CRDC/DataSubmissions/Validation/ValidationResults_AggregatedExpanded-Btn"
VR_NODE = "CRDC/DataSubmissions/Validation/ValidationResults_NodeType-Ddn"
VR_SEVERITY = "CRDC/DataSubmissions/Validation/ValidationResults_Severity-Ddn"
VR_ISSUE = "CRDC/DataSubmissions/Validation/ValidationResults_IssueType-Ddn"
VR_HEADERS = "CRDC/DataSubmissions/Validation/Table-Headers"
VR_ROW = "CRDC/DataSubmissions/Validation/Table-Row"
VR_EXPORT = "CRDC/DataSubmissions/Validation/Download-Btn-ValidationResults"
_EXPORT_DOWNLOAD_DIR = repo_root() / "test-results" / "downloads"

ERR_DIALOG = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/Dialog"
ERR_LIST = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/ErrorList-Container"
ERR_ITEM = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/ErrorList-Item"

# Upload Activities tab: batch table rows, the "N Errors" link, and column names to look up.
_UA_ROW = "CRDC/AILocators/GenericTable/TableRow"
_UA_ERROR_COUNT = "CRDC/AILocators/DataSubmissions/Detail/UploadActivity/ErrorCount-Btn"
_UA_TYPE_HEADERS = ("Batch Type", "Type")
_UA_FILE_COUNT_HEADERS = ("File Count", "Files")
_UA_STATUS_HEADERS = ("Status",)
ERR_CLOSE = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/Close-Btn"
ERR_SEVERITY = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/IssueSeverity-Lbl"
ERR_MESSAGE = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/IssueMessage-Lbl"

SUMMARY_SUBMISSION_NAME = "CRDC/AILocators/DataSubmissions/Detail/Summary/SubmissionName-Lbl"
SUMMARY_STATUS = "CRDC/AILocators/DataSubmissions/Detail/Summary/Status-Lbl"
VALIDATE_CONTROL = "CRDC/AILocators/DataSubmissions/Detail/ValidationControls/Validate-Btn"
VALIDATION_TYPE_METADATA = (
    "CRDC/AILocators/DataSubmissions/Detail/ValidationControls/ValidationType-Metadata-RadioBtn"
)
VALIDATION_TARGET_ALL = (
    "CRDC/AILocators/DataSubmissions/Detail/ValidationControls/ValidationTarget-AllUploadedData-RadioBtn"
)
VALIDATION_TARGET_NEW = (
    "CRDC/AILocators/DataSubmissions/Detail/ValidationControls/ValidationTarget-NewUploadedData-RadioBtn"
)
SUMMARY_COLLABORATORS_BTN = "CRDC/AILocators/DataSubmissions/Detail/Summary/Collaborators-Btn"
SUMMARY_HEADER_ROOT = "CRDC/AILocators/DataSubmissions/Detail/Summary/SummaryHeader-Root"
_TRUNCATED = 15
_UPLOAD_MS = 60_000
# PBAC single-TSV upload (Katalon uploadMetadataUI parity) — longer than upload_folder.
_PBAC_UPLOAD_HIDDEN_MS = 120_000
_PBAC_VALIDATE_ENABLE_S = 120

_ACTION_SUBMIT = "CRDC/AILocators/DataSubmissions/Detail/Actions/Submit-Btn"
_SUBMIT_DIALOG = "CRDC/AILocators/DataSubmissions/SubmitDialog/Dialog"
_SUBMIT_DIALOG_YES = "CRDC/AILocators/DataSubmissions/SubmitDialog/Confirm-Btn"
_CROSS_VALIDATE = "CRDC/AILocators/DataSubmissions/Detail/ValidationControls/CrossValidate-Btn"
_ACTION_RELEASE = "CRDC/AILocators/DataSubmissions/Detail/Actions/Release-Btn"
_RELEASE_CONFIRMATION_YES = "CRDC/AILocators/DataSubmissions/Detail/Actions/ReleaseConfirmationYes-Btn"
_ACTION_COMPLETE = "CRDC/AILocators/DataSubmissions/Detail/Actions/Complete-Btn"
_ACTION_REJECT = "CRDC/AILocators/DataSubmissions/Detail/Actions/Reject-Btn"
_ACTION_WITHDRAW = "CRDC/AILocators/DataSubmissions/Detail/Actions/Withdraw-Btn"
_ACTION_ADMIN_SUBMIT = "CRDC/AILocators/DataSubmissions/Detail/Actions/AdminSubmit-Btn"
_ACTION_CANCEL = "CRDC/AILocators/DataSubmissions/Detail/Actions/Cancel-Btn"
_ACTION_REJECT_COMMENT = "CRDC/AILocators/DataSubmissions/Detail/Actions/RejectDsComment-Txtbx"
_ACTION_CONFIRM_REJECT = "CRDC/AILocators/DataSubmissions/Detail/Actions/ConfirmToReject-Btn"
_COMPLETE_CONFIRMATION_YES = "CRDC/AILocators/DataSubmissions/Detail/Actions/CompleteConfirmationYes-Btn"
SUMMARY_FULL_HISTORY = "CRDC/AILocators/DataSubmissions/Detail/Summary/FullHistory-Btn"
HISTORY_DIALOG = "CRDC/AILocators/DataSubmissions/HistoryDialog/Dialog"
HISTORY_CLOSE = "CRDC/AILocators/DataSubmissions/HistoryDialog/Close-Btn"
HISTORY_ITEM_STATUS = "CRDC/AILocators/DataSubmissions/HistoryDialog/Item-Status"
HISTORY_ITEM0_STATUS = "CRDC/AILocators/DataSubmissions/HistoryDialog/Item0-Status"
CV_TAB = "CRDC/AILocators/DataSubmissions/Detail/Tabs/CrossValidation-Tab"
CV_TABLE = "CRDC/AILocators/DataSubmissions/Detail/CrossValidation/Table"
CV_TABLE_ROW = "CRDC/AILocators/DataSubmissions/Detail/CrossValidation/Table-DataRow"
_CV_ROWS_PER_PAGE = 50
_CV_REQUIRED_COLUMNS = ("Submitted Identifier", "Node Type", "Severity")


def _header_index(names: list[str], wanted: str) -> int:
    """Column index by header label, case-insensitive. -1 if missing."""
    wanted_l = wanted.lower()
    for i, name in enumerate(names):
        if name.lower() == wanted_l:
            return i
    return -1


class DataSubmissionDetailPage(BasePage):
    """Open submission: metadata upload, Validate, Validation Results table."""

    VALIDATE_MS = 300_000

    @property
    def upload_model_version(self) -> Locator:
        """Step 1 UPLOAD METADATA line that names the data model and version.

        The page shows it in capitals (for example SDM DATA MODEL: v0.0.3) but the element text
        is "SDM Data Model: v0.0.3", so an expect on text sees the mixed-case form.
        """
        return self._loc(UPLOAD_MODEL_VERSION)

    @property
    def collaborators_button(self) -> Locator:
        """Collaborators control on the summary header (tooltip hover target)."""
        return self._loc(SUMMARY_COLLABORATORS_BTN)

    @property
    def status_label(self) -> Locator:
        """Submission status in the summary header (Submitted, Rejected, ...)."""
        return self._loc(SUMMARY_STATUS)

    @property
    def validate_button(self) -> Locator:
        """Validate button in the validation controls."""
        return self._loc(VALIDATE_CONTROL)

    @property
    def validation_type_metadata_radio(self) -> Locator:
        """Validation Type: Metadata."""
        return self._loc(VALIDATION_TYPE_METADATA)

    @property
    def validation_target_all_radio(self) -> Locator:
        """Validation Target: All Uploaded Data."""
        return self._loc(VALIDATION_TARGET_ALL)

    @property
    def validation_target_new_radio(self) -> Locator:
        """Validation Target: New Uploaded Data."""
        return self._loc(VALIDATION_TARGET_NEW)

    @property
    def reject_button(self) -> Locator:
        """Reject action (Dcp or Fedlead on a Submitted submission)."""
        return self._loc(_ACTION_REJECT)

    @property
    def reject_comment(self) -> Locator:
        """Reject justification text box in the reject dialog."""
        return self._loc(_ACTION_REJECT_COMMENT)

    @property
    def confirm_reject_button(self) -> Locator:
        """Confirm to Reject button in the reject dialog."""
        return self._loc(_ACTION_CONFIRM_REJECT)

    @property
    def cross_validate_button(self) -> Locator:
        """Cross Validate button in the validation controls."""
        return self._loc(_CROSS_VALIDATE)

    @property
    def complete_button(self) -> Locator:
        """Complete action (after Release)."""
        return self._loc(_ACTION_COMPLETE)

    @property
    def complete_confirmation_yes(self) -> Locator:
        """Yes button on the Complete confirmation dialog."""
        return self._loc(_COMPLETE_CONFIRMATION_YES)

    @property
    def full_history_button(self) -> Locator:
        """Full History button in the summary header."""
        return self._loc(SUMMARY_FULL_HISTORY)

    @property
    def history_dialog(self) -> Locator:
        """Submission History dialog."""
        return self._loc(HISTORY_DIALOG)

    @property
    def history_close_button(self) -> Locator:
        """Close button of the Submission History dialog."""
        return self._loc(HISTORY_CLOSE)

    def read_history_statuses(self) -> list[str]:
        """Status text of each Submission History row, newest first (dialog must be open).

        Waits for the first row so the full list is rendered before reading (as Katalon does).
        """
        self._loc(HISTORY_ITEM0_STATUS).first.wait_for(state="visible", timeout=10_000)
        cells = self._loc(HISTORY_ITEM_STATUS)
        texts = [(cells.nth(i).inner_text() or "").strip() for i in range(cells.count())]
        return [t for t in texts if t]

    def read_cross_validation_rows_for_peer(self, peer_submission_id: str) -> list[CrossValidationRow]:
        """Open Cross Validation Results and read the rows that link to a peer submission.

        Returns (Submitted Identifier, Node Type, Severity, Issues) for every row, across
        all pages, whose Conflicting Submission link points at peer_submission_id (Katalon
        readCrossValidationRowsForConflictingSubmission). Raises if a required column is
        missing or no row links to the peer.
        """
        self._loc(CV_TAB).first.click()
        self.wait_loading_spinner_gone()
        self._loc(CV_TABLE_ROW).first.wait_for(state="visible", timeout=30_000)
        self.change_rows_per_page(_CV_ROWS_PER_PAGE)

        headers = self._read_table_headers(self._loc(CV_TABLE))
        lowered = [h.lower() for h in headers]
        for name in _CV_REQUIRED_COLUMNS:
            if name.lower() not in lowered:
                raise AssertionError(f"Cross Validation table has no {name!r} column; headers are {headers}")
        id_i, node_i, severity_i = (lowered.index(n.lower()) for n in _CV_REQUIRED_COLUMNS)
        issues_i = lowered.index("issues") if "issues" in lowered else next(
            (i for i, h in enumerate(lowered) if "issue" in h), -1
        )

        peer_link = self.page.locator(f"[data-testid='conflicting-link-{peer_submission_id.strip()}']")
        peer_rows = self._loc(CV_TABLE_ROW).filter(has=peer_link)

        def cell(cells: list[str], index: int) -> str:
            return cells[index].strip() if 0 <= index < len(cells) else ""

        matched: list[CrossValidationRow] = []
        while True:
            self.wait_for_generic_table_settled()
            for cells in self._read_table_rows_full_text(peer_rows):
                matched.append(
                    (cell(cells, id_i), cell(cells, node_i), cell(cells, severity_i), cell(cells, issues_i))
                )
            current, total = self.read_current_page(), self.read_total_pages()
            if current is None or total is None or current >= total:
                break
            self.go_to_next_page()
        if not matched:
            raise AssertionError(
                f"no Cross Validation rows link to peer submission {peer_submission_id!r}"
            )
        log.info("Read %s Cross Validation row(s) for peer %s", len(matched), peer_submission_id)
        return matched

    @property
    def submission_name_tooltip_trigger(self) -> Locator:
        """Value cell beside Submission Name (hover for full name tooltip)."""
        return self._summary_label_value_sibling("Submission Name")

    def read_summary_header(self) -> dict[str, str]:
        """Summary panel fields as submission_name, submitter, submission_type, collaborators, study, data_commons, program, data_concierge."""
        self._loc(SUMMARY_SUBMISSION_NAME).wait_for(state="visible")
        submission_name = self._read_submission_name_display()
        return {
            "submission_name": submission_name,
            "submitter": self._summary_value_by_label_or_aria("Submitter"),
            "submission_type": self._summary_value_by_label("Submission Type"),
            "collaborators": (self.collaborators_button.inner_text() or "").strip(),
            "study": self._summary_value_by_label("Study"),
            "data_commons": self._summary_value_by_label("Data Commons"),
            "program": self._summary_value_by_label("Program"),
            "data_concierge": self._summary_value_by_label_or_aria("Data Concierge"),
        }

    def verify_summary_header_fields(
        self,
        expected: Mapping[str, str],
        *,
        actual: dict[str, str] | None = None,
    ) -> None:
        """Assert summary header values after whitespace normalization (Katalon compareAndReport)."""
        if actual is None:
            actual = self.read_summary_header()
        log.info("Verifying data submission summary header (%d fields)", len(expected))
        failures: list[str] = []
        for key, expected_raw in expected.items():
            label = _SUMMARY_HEADER_LABELS.get(key, key)
            exp = normalize_summary_header_value(expected_raw)
            act = normalize_summary_header_value(actual.get(key, ""))
            status = "Pass" if exp == act else "Fail"
            log.info(
                "Summary header %s | expected: %s | actual: %s | %s",
                label,
                exp or "(empty)",
                act or "(empty)",
                status,
            )
            if exp != act:
                failures.append(f"{label}: expected {exp!r}, got {act!r}")
        if failures:
            raise AssertionError("Summary header mismatch:\n" + "\n".join(failures))

    def _read_submission_name_display(self) -> str:
        """Full submission name: sibling value cell aria-label (Katalon getHeaderValueByLabelOrAria), then label fallbacks."""
        from_sibling = self._summary_value_by_label_or_aria("Submission Name")
        if from_sibling:
            return from_sibling
        label = self._loc(SUMMARY_SUBMISSION_NAME)
        aria = label.get_attribute("aria-label")
        if aria:
            return aria.strip()
        return (label.inner_text() or "").strip()

    def _summary_header_xpath_root(self) -> str:
        """Detail summary strip (avoids list filters that also mention Submitter)."""
        return self.locators.get(SUMMARY_HEADER_ROOT)

    def _summary_label_value_sibling(self, label: str) -> Locator:
        """Value cell immediately after a summary label (Hub truncated-text-label rows)."""
        lit = self._xpath_literal(label)
        root = self._summary_header_xpath_root()
        exact = self.page.locator(
            f"{root}//*[@data-testid='truncated-text-label'][normalize-space(.)={lit}]"
            "/following-sibling::*[1]"
        )
        if exact.count() > 0:
            return exact.first
        loose = self.page.locator(
            f"{root}//*[@data-testid='truncated-text-label'][contains(normalize-space(.), {lit})]"
            "/following-sibling::*[1]"
        )
        if loose.count() > 0:
            return loose.first
        return self.page.locator(
            f"{root}//*[contains(normalize-space(.), {lit})]/following-sibling::*[1]"
        ).first

    def _summary_value_by_label(self, label: str) -> str:
        sibling = self._summary_label_value_sibling(label)
        cells = sibling.locator(
            "[data-testid='property-value'], [data-testid='submission-name-display']"
        )
        if cells.count() > 0:
            return (cells.first.inner_text() or "").strip()
        return (sibling.inner_text() or "").strip()

    def _summary_value_by_label_or_aria(self, label: str) -> str:
        sibling = self._summary_label_value_sibling(label)
        wrapper = sibling.locator("[data-testid='truncated-text-wrapper']")
        if wrapper.count() > 0:
            aria = wrapper.first.get_attribute("aria-label")
            if aria:
                return aria.strip()
        text = self._summary_value_by_label(label)
        if text:
            return text
        return (sibling.inner_text() or "").strip()

    @staticmethod
    def _xpath_literal(text: str) -> str:
        if "'" not in text:
            return f"'{text}'"
        if '"' not in text:
            return f'"{text}"'
        parts = text.split("'")
        return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"

    def upload_folder(self, tc_name: str, root: Path | None = None) -> None:
        """Choose every top-level TSV in MetadataData/<tcName>, Upload, and wait until Uploading is gone (skips expected-ValidationResults)."""
        files, _nodes = list_tsv_files_and_nodes_for_tc(tc_name, root=root or repo_root())
        if not files:
            return
        chooser = self._loc(CHOOSE_FILES)
        chooser.wait_for(state="attached")
        chooser.set_input_files([str(path) for path in files])
        self._loc(UPLOAD).click()
        uploading = self._loc(UPLOADING).first
        try:
            uploading.wait_for(state="visible", timeout=self.PROBE_MS)
        except PlaywrightTimeoutError:
            pass
        uploading.wait_for(state="hidden", timeout=_UPLOAD_MS)
        log.info("Upload finished for %s (%s files)", tc_name, len(files))

    def click_validate(self) -> None:
        """Click Validate, wait until disabled then enabled again (Katalon up to 5 minutes)."""
        btn = self._loc(VALIDATE)
        expect(btn).to_be_enabled(timeout=30_000)
        btn.click()
        log.info("Waiting for Validation to finish - waiting up to 5 minutes")
        expect(btn).to_be_disabled(timeout=self.DEFAULT_MS)
        expect(btn).to_be_enabled(timeout=self.VALIDATE_MS)
        log.info("Validation finished; Validate is enabled again")

    def upload_metadata_file(self, absolute_path: Path) -> None:
        """Choose one TSV, Upload, wait for ingest, then wait until Validate enables (PBAC / Katalon uploadMetadataUI).

        Uses longer timeouts than upload_folder for large ingest on QA.
        """
        path = absolute_path.resolve()
        log.info("DS PBAC: uploading metadata file %s", path)
        choose = self._loc(CHOOSE_FILES)
        choose.wait_for(state="attached")
        choose.set_input_files(str(path))
        self._loc(UPLOAD).click()
        log.info("DS PBAC: waiting for Uploading indicator to clear")
        uploading = self._loc(UPLOADING).first
        try:
            uploading.wait_for(state="visible", timeout=2_000)
        except PlaywrightTimeoutError:
            pass
        uploading.wait_for(state="hidden", timeout=_PBAC_UPLOAD_HIDDEN_MS)
        log.info("DS PBAC: upload finished; waiting for Validate to enable")
        validate_btn = self._loc(VALIDATE)
        validate_btn.wait_for(state="visible")
        deadline = datetime.now().timestamp() + _PBAC_VALIDATE_ENABLE_S
        while datetime.now().timestamp() < deadline:
            if validate_btn.is_enabled():
                log.info("DS PBAC: Validate is enabled after upload")
                return
            self.page.wait_for_timeout(300)
        raise AssertionError("Validate did not become enabled after metadata upload")

    def click_submit_for_review(self) -> None:
        """Submit → confirm dialog Yes → wait for dialog to close (do not wait on detached Yes button)."""
        submit = self._loc(_ACTION_SUBMIT).first
        log.info("DS PBAC: waiting for Submit action")
        submit.wait_for(state="visible", timeout=30_000)
        submit.click()
        dialog = self._loc(_SUBMIT_DIALOG)
        yes_btn = self._loc(_SUBMIT_DIALOG_YES).first
        log.info("DS PBAC: waiting for submit dialog (data-testid=submit-dialog)")
        dialog.wait_for(state="visible", timeout=30_000)
        expect(yes_btn).to_be_visible(timeout=30_000)
        expect(yes_btn).to_be_enabled(timeout=30_000)
        log.info("DS PBAC: clicking submit dialog Yes (Confirm-Btn)")
        yes_btn.click()
        log.info("DS PBAC: waiting for submit dialog to close")
        dialog.wait_for(state="hidden", timeout=30_000)

    def click_release_confirmation_yes(self) -> None:
        """After Release, click the primary Yes on the confirmation dialog (Katalon SubmitYes-Btn parity)."""
        yes_btn = self._loc(_RELEASE_CONFIRMATION_YES).first
        log.info("DS PBAC (confirm): waiting for Release confirmation Yes button")
        expect(yes_btn).to_be_visible(timeout=30_000)
        expect(yes_btn).to_be_enabled(timeout=30_000)
        log.info("DS PBAC (confirm): clicking Yes (Katalon SubmitYes-Btn parity)")
        yes_btn.click()

    def click_cross_validate(self) -> None:
        """Cross-validate control before Release (data_submission:confirm positive path)."""
        self._loc(_CROSS_VALIDATE).first.click()

    def click_release(self) -> None:
        """Release action after cross-validation."""
        btn = self._loc(_ACTION_RELEASE).first
        log.info("DS PBAC (confirm): waiting for Release action")
        btn.wait_for(state="visible", timeout=30_000)
        btn.click()

    def is_admin_submit_enabled(self, *, timeout_ms: int = 30_000) -> bool:
        """True if Admin Submit is visible and enabled (after validate with invalid metadata)."""
        admin_submit = self._loc(_ACTION_ADMIN_SUBMIT).first
        try:
            admin_submit.wait_for(state="visible", timeout=timeout_ms)
        except Exception:
            return False
        return admin_submit.is_enabled()

    def is_cancel_visible(self) -> bool:
        """Cancel action on draft detail (PBAC data_submission:cancel)."""
        return self._loc(_ACTION_CANCEL).first.is_visible()

    def release_reject_flags(self) -> tuple[bool, bool]:
        """Release and Reject visibility (PBAC data_submission:review).

        Withdraw is owner chrome after Submit, not a Review permission. Do not score it here.
        """
        release = self._loc(_ACTION_RELEASE).first
        reject = self._loc(_ACTION_REJECT).first
        return release.is_visible(), reject.is_visible()

    def complete_reject_flags(self) -> tuple[bool, bool]:
        """Complete and Reject visibility after release confirmation (PBAC data_submission:confirm)."""
        complete = self._loc(_ACTION_COMPLETE).first
        reject = self._loc(_ACTION_REJECT).first
        return complete.is_visible(), reject.is_visible()

    def is_cross_validate_or_release_or_complete_any_visible(self) -> bool:
        """Negative confirm check: any of cross-validate / release / complete (PBAC submitter negative)."""
        cross = self._loc(_CROSS_VALIDATE).first
        release = self._loc(_ACTION_RELEASE).first
        complete = self._loc(_ACTION_COMPLETE).first
        return cross.is_visible() or release.is_visible() or complete.is_visible()

    def open_validation_results(self) -> None:
        """Validation Results tab, then aggregated/expanded view with filters visible."""
        self._loc(VR_TAB).click()
        self.wait_loading_spinner_gone()
        self._ensure_validation_results_expanded()

    # --- Validation Results export (Katalon CRDCDH-1035) ---

    def submission_id_from_url(self) -> str:
        """Submission id (UUID) from the current URL (Katalon getSubmissionIdFromUploadActivityUrl)."""
        # data_submissions_list imports this module, so import it here, not at the top.
        from crdc_pw.pages.data_submissions_list import parse_submission_id_from_text

        submission_id = parse_submission_id_from_text(self.page.url)
        if not submission_id:
            raise AssertionError(f"No submission id in URL {self.page.url!r}")
        log.info("Submission ID: %s", submission_id)
        return submission_id

    def open_upload_activity(self, submission_id: str) -> None:
        """Open a submission's upload-activity page by id (Katalon navigateToSubmissionUploadActivity)."""
        url = f"{self._hub.settings.base_url.rstrip('/')}/data-submission/{submission_id}/upload-activity"
        log.info("Navigating to URL: %s", url)
        self.page.goto(url, wait_until="domcontentloaded")
        self._loc(VR_TAB).wait_for(state="visible")
        self.wait_loading_spinner_gone()

    def verify_validation_results_export_enabled(self) -> None:
        """Validation Results tab: the export button is visible and enabled (Katalon verifyButtonEnabled true)."""
        self._loc(VR_TAB).click()
        self.wait_loading_spinner_gone()
        # The table has an export icon above and below it; Katalon used the first match.
        export = self._loc(VR_EXPORT).first
        export.wait_for(state="visible")
        expect(export).to_be_enabled()
        log.info("Validation Results export button is enabled for %s", self._hub.role)

    def export_validation_results_and_verify_filename(
        self, submission_name: str, *, timeout_s: float = 60
    ) -> Path:
        """Click Export on the Validation Results tab, save the download and check its file name.

        Katalon clicked, slept, and read the newest file in Downloads; this waits for the
        download event instead. Returns the saved path under test-results/downloads.
        """
        _EXPORT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with self.page.expect_download(timeout=timeout_s * 1000) as download_info:
            self._loc(VR_EXPORT).first.click()
        download = download_info.value
        name = download.suggested_filename or ""
        problem = check_export_filename(name, submission_name)
        if problem:
            raise AssertionError(f"Validation Results export: {problem}")
        dest = _EXPORT_DOWNLOAD_DIR / name
        download.save_as(dest)
        log.info("Validation Results export verified: %s", name)
        return dest

    def _vr_node_filter_visible(self) -> bool:
        try:
            self._loc(VR_NODE).first.wait_for(state="visible", timeout=self.PROBE_MS)
            return True
        except PlaywrightTimeoutError:
            return False

    def _ensure_validation_results_expanded(self) -> None:
        if self._vr_node_filter_visible():
            return
        for attempt in range(2):
            log.info(
                "Validation Results filters not visible; toggling aggregated/expanded (attempt %s)",
                attempt + 1,
            )
            self._loc(VR_EXPANDED).click()
            self.wait_loading_spinner_gone()
            if self._vr_node_filter_visible():
                return
        raise RuntimeError(
            "Validation Results node filter did not become visible after toggling aggregated/expanded"
        )

    def apply_vr_filters(self, node: str, severity: str, issue_type: str) -> None:
        """Set node, severity, and issue type filters and wait for the Validation Results table to settle."""
        display_node = node.replace("datafile", "data file") if node == "datafile" else node
        self.wait_loading_spinner_gone()
        self._select_li(self._loc(VR_NODE), display_node)
        self._select_li(self._loc(VR_SEVERITY), severity)
        self.wait_loading_spinner_gone()
        self._select_li(self._loc(VR_ISSUE), issue_type)
        self.wait_loading_spinner_gone()
        rows = self._loc(VR_ROW)
        self.wait_for_generic_table_settled(rows)

    def read_vr_rows(self) -> list[tuple[str, str, str]]:
        """Each Validation Results row as (submitted identifier, issue type, severity), with full text from truncated cells."""
        header_names = [(el.inner_text() or "").strip() for el in self._loc(VR_HEADERS).all()]
        idx_submitted = _header_index(header_names, "Submitted Identifier")
        idx_issue = _header_index(header_names, "Issue Type")
        if idx_issue < 0:
            idx_issue = _header_index(header_names, "Issue(s)")
        if idx_issue < 0:
            idx_issue = next((i for i, name in enumerate(header_names) if "issue" in name.lower()), -1)
        idx_sev = _header_index(header_names, "Severity")
        if idx_submitted < 0 or idx_sev < 0:
            raise RuntimeError(
                "Validation Results table missing required columns (Submitted Identifier, Severity). "
                f"Headers: {header_names}"
            )
        rows = self._loc(VR_ROW)
        out: list[tuple[str, str, str]] = []
        for i in range(rows.count()):
            cells = rows.nth(i).locator("td")
            submitted = self._cell_text(cells, idx_submitted)
            issue = self._cell_text(cells, idx_issue) if idx_issue >= 0 else ""
            sev = self._cell_text(cells, idx_sev)
            out.append((submitted, issue, sev))
        return out

    def verify_validation_results_vs_expected_for_tc(self, tc_name: str, model: str) -> None:
        """Compare the VR table to expected TSVs for each node, severity, and issue type (Katalon verifyValidationResultsVsExpectedForTC)."""
        self.open_validation_results()
        nodes = list_nodes_from_expected_validation_results_folder(tc_name)
        if not nodes:
            log.info(
                "verifyValidationResultsVsExpectedForTC: No expected Validation Results files for TC '%s'; skipping.",
                tc_name,
            )
            return
        mappings = load_validation_results_mappings(model)
        errors: list[str] = []
        for node in nodes:
            tsv_path = find_expected_validation_results_tsv(tc_name, node)
            if tsv_path is None:
                log.info(
                    "verifyValidationResultsVsExpectedForTC: No expected TSV for node '%s'; skipping.",
                    node,
                )
                continue
            column = mappings.get(node)
            if not column:
                raise RuntimeError(
                    f"verifyValidationResultsVsExpected: no mapping for node '{node}' in ValidationResults-Mappings"
                )
            for severity, issue_type in unique_severity_issue_type_pairs_from_expected_tsv(tsv_path):
                log.info(
                    "--- Verifying Validation Results for node: %s, severity: %s, issueType: %s ---",
                    node,
                    severity,
                    issue_type,
                )
                expected = load_expected_validation_results_tsv(tsv_path, column, severity, issue_type)
                self.apply_vr_filters(node, severity, issue_type)
                actual = self.read_vr_rows()
                pair_errors = diff_validation_results(expected, actual, issue_type)
                if pair_errors:
                    log.info(
                        "--- Validation Results vs Expected (%s, %s, %s) - %s issue(s) ---",
                        node,
                        severity,
                        issue_type,
                        len(pair_errors),
                    )
                    for err in pair_errors:
                        log.info(err)
                    log.info("--- end ---")
                    errors.extend(pair_errors)
                else:
                    log.info(
                        "Validation Results match expected for node=%s, severity=%s, issueType=%s",
                        node,
                        severity,
                        issue_type,
                    )
        if errors:
            raise AssertionError(
                f"verifyValidationResultsVsExpected: {len(errors)} mismatch(es). See log above."
            )

    def click_see_details_for_submitted_id(self, submitted_identifier: str) -> None:
        """Open See details on the VR row whose Submitted Identifier matches (case-insensitive)."""
        target = (submitted_identifier or "").strip()
        if not target:
            raise RuntimeError("click_see_details_for_submitted_id: empty submitted identifier")
        header_names = [(el.inner_text() or "").strip() for el in self._loc(VR_HEADERS).all()]
        idx_submitted = _header_index(header_names, "Submitted Identifier")
        if idx_submitted < 0:
            raise RuntimeError(
                f"click_see_details_for_submitted_id: Submitted Identifier column not found. Headers: {header_names}"
            )
        rows = self._loc(VR_ROW)
        matching: Locator | None = None
        for i in range(rows.count()):
            cells = rows.nth(i).locator("td")
            cell_text = self._cell_text(cells, idx_submitted)
            if cell_text.strip().lower() == target.lower():
                matching = rows.nth(i)
                break
        if matching is None:
            raise AssertionError(
                f"click_see_details_for_submitted_id: no row with Submitted Identifier '{submitted_identifier}'"
            )
        matching.locator("button").filter(has_text="See details").click()
        self._loc(ERR_DIALOG).wait_for(state="visible", timeout=10_000)
        log.info("click_see_details_for_submitted_id: opened error details dialog for %s", target)

    def read_error_details_dialog_issues(self) -> list[dict[str, str]]:
        """Each open error-details dialog issue as a dict with keys severity and message."""
        severities = self._loc(ERR_SEVERITY)
        messages = self._loc(ERR_MESSAGE)
        count = min(severities.count(), messages.count())
        issues: list[dict[str, str]] = []
        for i in range(count):
            issues.append(
                {
                    "severity": (severities.nth(i).inner_text() or "").strip(),
                    "message": (messages.nth(i).inner_text() or "").strip(),
                }
            )
        log.info("read_error_details_dialog_issues: found %d issue(s)", len(issues))
        return issues

    def close_error_details_dialog(self) -> None:
        """Close the error-details dialog and wait until it is hidden."""
        self._loc(ERR_CLOSE).click()
        self._loc(ERR_DIALOG).wait_for(state="hidden", timeout=5_000)

    # --- Upload Activities tab (Katalon verifyUploadActivitiesBatchRow / FailedErrorsModal) ---

    @staticmethod
    def _first_header_index(names: list[str], candidates: tuple[str, ...]) -> int:
        """Index of the first header equal (case-insensitive) to any candidate, in candidate order."""
        for candidate in candidates:
            index = _header_index(names, candidate)
            if index >= 0:
                return index
        return -1

    def _upload_batch_row_problem(
        self, batch_type: str, expected_file_count: int, expected_status: str
    ) -> str | None:
        """None when some Upload Activities row matches type, file count and status, else why not."""
        headers = [" ".join(text.split()) for text in self._loc(VR_HEADERS).all_inner_texts()]
        type_i = self._first_header_index(headers, _UA_TYPE_HEADERS)
        count_i = self._first_header_index(headers, _UA_FILE_COUNT_HEADERS)
        status_i = self._first_header_index(headers, _UA_STATUS_HEADERS)
        if min(type_i, count_i, status_i) < 0:
            return f"Batch Type, File Count or Status column not found; headers are {headers}"
        rows = self._read_table_rows_full_text(self._loc(_UA_ROW))
        if not rows:
            return "no batch rows in the Upload Activities table"
        seen: list[tuple[str, str, str]] = []
        for cells in rows:
            if len(cells) <= max(type_i, count_i, status_i):
                continue
            row_type, count_text, row_status = cells[type_i], cells[count_i], cells[status_i]
            seen.append((row_type, count_text, row_status))
            digits = re.sub(r"\D", "", count_text)
            if (
                row_type.strip().lower() == batch_type.strip().lower()
                and digits
                and int(digits) == expected_file_count
                and row_status.strip().lower() == expected_status.strip().lower()
            ):
                return None
        return (
            f"no {batch_type} batch with {expected_file_count} file(s) and status "
            f"{expected_status!r}; rows seen (type, files, status): {seen}"
        )

    def verify_upload_activities_batch_row(
        self, batch_type: str, expected_file_count: int, expected_status: str
    ) -> None:
        """Upload Activities has a batch of batch_type with expected_file_count files and expected_status.

        Polls up to the Hub default, because a batch can still read Uploading just after the
        upload indicator clears. Katalon stopped at the first row of the right type; this
        passes if any row matches.
        """
        if not expected_status.strip():
            raise ValueError("verify_upload_activities_batch_row: expected_status is required")
        self._poll_until(
            lambda: self._upload_batch_row_problem(batch_type, expected_file_count, expected_status)
            is None
        )
        problem = self._upload_batch_row_problem(batch_type, expected_file_count, expected_status)
        if problem:
            raise AssertionError(f"Upload Activities batch row: {problem}")
        log.info(
            "Upload Activities: found %s batch, %s file(s), status %s",
            batch_type,
            expected_file_count,
            expected_status,
        )

    def read_upload_errors_modal_messages(self) -> list[str]:
        """Messages in the open Upload Errors modal, without the leading "1. " numbering.

        Reads the numbered list items; if none are numbered, splits the container text on
        the numbers (Katalon fallback).
        """
        self._loc(ERR_LIST).wait_for(state="visible", timeout=10_000)
        numbered = [text.strip() for text in self._loc(ERR_ITEM).all_inner_texts()]
        messages = [
            re.sub(r"^\d+\.\s*", "", text)
            for text in numbered
            if re.match(r"\d+\.\s+.+", text)
        ]
        if messages:
            return messages
        container_text = self._loc(ERR_LIST).first.inner_text() or ""
        return [part.strip() for part in re.split(r"\d+\.\s", container_text)[1:] if part.strip()]

    def verify_upload_errors_modal(self, tc_name: str) -> None:
        """Open the first Upload Errors link and compare the modal with expected/*.tsv for tc_name.

        The two lists must be equal ignoring order and curly versus straight quotes; the
        modal is always closed again.
        """
        expected = load_expected_upload_errors(tc_name)
        link = self._loc(_UA_ERROR_COUNT).first
        try:
            link.wait_for(state="visible", timeout=10_000)
        except PlaywrightTimeoutError:
            raise AssertionError("Upload Errors link not found on the Upload Activities tab") from None
        link.click()
        self._loc(ERR_DIALOG).wait_for(state="visible", timeout=10_000)
        try:
            actual = self.read_upload_errors_modal_messages()
        finally:
            try:
                self.close_error_details_dialog()
            except PlaywrightTimeoutError:
                log.info("Upload Errors modal did not close cleanly")
        missing, extra = diff_upload_errors(expected, actual)
        log.info("Upload Errors modal: expected %d, actual %d", len(expected), len(actual))
        if missing or extra:
            raise AssertionError(
                f"Upload Errors modal for {tc_name}: expected {len(expected)} error(s), "
                f"actual {len(actual)}. Expected but not shown: {missing[:3]}"
                f"{'...' if len(missing) > 3 else ''}. Shown but not expected: {extra[:3]}"
                f"{'...' if len(extra) > 3 else ''}"
            )

    def verify_error_details_for_submitted_id(
        self,
        submitted_identifier: str,
        expected_issues: list[dict[str, str]],
    ) -> None:
        """See details for one row, assert dialog issues against expected, then close the dialog."""
        self.click_see_details_for_submitted_id(submitted_identifier)
        actual = self.read_error_details_dialog_issues()
        errors = diff_error_details_dialog_issues(expected_issues, actual)
        self.close_error_details_dialog()
        if errors:
            for err in errors:
                log.info(err)
            raise AssertionError(
                f"verifyErrorDetailsForSubmittedId '{submitted_identifier}': "
                f"{len(errors)} dialog issue mismatch(es)"
            )

    def verify_error_details_for_submitted_id_for_tc(self, tc_name: str, model: str) -> None:
        """For each expected TSV row with issues, filter VR, open See details, and assert the dialog (Katalon verifyErrorDetailsForSubmittedIdForTC)."""
        self.open_validation_results()
        nodes = list_nodes_from_expected_validation_results_folder(tc_name)
        if not nodes:
            log.info(
                "verifyErrorDetailsForSubmittedIdForTC: No expected Validation Results files for TC '%s'; skipping.",
                tc_name,
            )
            return
        mappings = load_validation_results_mappings(model)
        errors: list[str] = []
        for node in nodes:
            submitted_id_column = mappings.get(node)
            if not submitted_id_column:
                log.info(
                    "verifyErrorDetailsForSubmittedIdForTC: no mapping for node '%s'; skipping.",
                    node,
                )
                continue
            tsv_path = find_expected_validation_results_tsv(tc_name, node)
            if tsv_path is None:
                log.info(
                    "verifyErrorDetailsForSubmittedIdForTC: no expected TSV for node '%s'; skipping.",
                    node,
                )
                continue
            detail_rows = load_all_expected_error_detail_rows_from_tsv(tsv_path, submitted_id_column)
            if not detail_rows:
                log.info(
                    "verifyErrorDetailsForSubmittedIdForTC: no rows with issues for node '%s'; skipping.",
                    node,
                )
                continue
            for submitted_id, severity, issue_type, message in detail_rows:
                log.info(
                    "--- verifyErrorDetailsForSubmittedId: node=%s, submittedId=%s, severity=%s, issueType=%s ---",
                    node,
                    submitted_id,
                    severity,
                    issue_type,
                )
                self.apply_vr_filters(node, severity, issue_type)
                expected_issues = expected_error_detail_issues_for_row(severity, message)
                try:
                    self.verify_error_details_for_submitted_id(submitted_id, expected_issues)
                except AssertionError as exc:
                    errors.append(str(exc))
                    log.info("%s", exc)
                    try:
                        if self._loc(ERR_DIALOG).is_visible():
                            self.close_error_details_dialog()
                    except PlaywrightTimeoutError:
                        pass
        self._loc(VR_EXPANDED).click()
        self.wait_loading_spinner_gone()
        if errors:
            raise AssertionError(
                f"verifyErrorDetailsForSubmittedIdForTC: {len(errors)} mismatch(es). See log above."
            )

    def _select_li(self, dropdown: Locator, text: str) -> None:
        dropdown.first.wait_for(state="visible")
        dropdown.first.click()
        option = self.page.locator("//li").filter(has_text=re.compile(rf"^{re.escape(text)}$"))
        option.first.wait_for(state="visible")
        option.first.click()

    def _cell_text(self, cells: Locator, index: int) -> str:
        if index < 0 or index >= cells.count():
            return ""
        cell = cells.nth(index)
        raw = (cell.inner_text() or "").strip()
        if len(raw) <= _TRUNCATED:
            return raw
        wrapper = cell.locator("[data-testid='truncated-text-wrapper']")
        if wrapper.count() > 0:
            aria = wrapper.first.get_attribute("aria-label")
            if aria:
                return aria.strip()
        span = cell.locator("span")
        if span.count() > 0:
            aria = span.first.get_attribute("aria-label")
            if aria:
                return aria.strip()
            return (span.first.inner_text() or "").strip()
        return raw
