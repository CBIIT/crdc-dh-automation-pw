"""Data Submissions list, create dialog, and submission detail (upload / validate / VR).

Tests construct DataSubmissionsListPage from hub, then:
  open()                       — nav Data Submissions
  create_data_submission(...)  — dialog, then filter list and open the new row
  upload_folder / click_validate / verify_error_details_for_submitted_id_for_tc /
  verify_validation_results_vs_expected_for_tc on DataSubmissionDetailPage.
  TSV oracles stay in utils/validation_results.py.

YAML paths stay on this page. Tests do not import CRDC/... strings.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.base import BasePage
from crdc_pw.pages.header import HeaderPage
from crdc_pw.utils.validation_results import (
    diff_error_details_dialog_issues,
    diff_validation_results,
    expected_error_detail_issues_for_row,
    find_expected_validation_results_tsv,
    list_nodes_from_expected_validation_results_folder,
    list_tsv_files_and_nodes_for_tc,
    load_all_expected_error_detail_rows_from_tsv,
    load_expected_validation_results_tsv,
    load_validation_results_mappings,
    unique_severity_issue_type_pairs_from_expected_tsv,
)

log = logging.getLogger("crdc_pw.data_submissions")

# List page (filters + Create button + table rows)
CREATE_BTN = "CRDC/AILocators/DataSubmissions/List/Table/CreateDataSubmission-Btn"
FILTERS = "CRDC/AILocators/DataSubmissions/List/Filters/Filters-Container"
LIST_ROW = "CRDC/AILocators/GenericTable/TableRow"
LOADING_ROW = "CRDC/AILocators/GenericTable/LoadingRow"
NAME_FILTER = "CRDC/AILocators/DataSubmissions/List/Filters/SubmissionName-TxtBx"
# Katalon Object Repository path; xpath is //a[contains(@href,'/upload-activity')]
NAME_LINK = "CRDC/DataSubmissions/DataSubmissionName-Link"

# Create dialog radios and dropdowns
SUB_TYPE_DELETE = "CRDC/DataSubmissions/Create/SubTypeDelete-Btn"
SUB_TYPE_NEW = "CRDC/DataSubmissions/Create/SubTypeNewUpdate-Btn"
METADATA_ONLY = "CRDC/DataSubmissions/Create/MetadataOnly-Btn"
METADATA_FILES = "CRDC/DataSubmissions/Create/MetadataDataFiles-Btn"
DATA_COMMONS_DDN = "CRDC/DataSubmissions/Create/DataCommons-Ddn"
DATA_COMMONS_OPTION = "CRDC/DataSubmissions/Create/DataCommonsDdn-Option"
STUDY_DDN = "CRDC/DataSubmissions/Create/Study-Ddn"
STUDY_OPTION = "CRDC/DataSubmissions/Create/StudyDdn-Option"
# AILocators stand in for Katalon Create/SubmissionName-Field and Create/Create-Btn
SUBMISSION_NAME = "CRDC/AILocators/DataSubmissions/CreateDialog/SubmissionName-TxtBx"
DIALOG_CREATE = "CRDC/AILocators/DataSubmissions/CreateDialog/Create-Btn"
DIALOG = "CRDC/AILocators/DataSubmissions/CreateDialog/Dialog"

# Detail page: upload, Validate, Validation Results
CHOOSE_FILES = "CRDC/DataSubmissions/ChooseFiles-Btn"
UPLOAD = "CRDC/DataSubmissions/Upload-Btn"
UPLOADING = "CRDC/DataSubmissions/Validation/Uploading-Text"
VALIDATE = "CRDC/DataSubmissions/Validate-Btn"
LOADING_ICON = "CRDC/DataSubmissions/Loading-Icon"
VR_TAB = "CRDC/DataSubmissions/Validation/ValidationResults-Tab"
VR_EXPANDED = "CRDC/DataSubmissions/Validation/ValidationResults_AggregatedExpanded-Btn"
VR_NODE = "CRDC/DataSubmissions/Validation/ValidationResults_NodeType-Ddn"
VR_SEVERITY = "CRDC/DataSubmissions/Validation/ValidationResults_Severity-Ddn"
VR_ISSUE = "CRDC/DataSubmissions/Validation/ValidationResults_IssueType-Ddn"
VR_HEADERS = "CRDC/DataSubmissions/Validation/Table-Headers"
VR_ROW = "CRDC/DataSubmissions/Validation/Table-Row"

ERR_DIALOG = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/Dialog"
ERR_CLOSE = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/Close-Btn"
ERR_SEVERITY = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/IssueSeverity-Lbl"
ERR_MESSAGE = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/IssueMessage-Lbl"

_UUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
# Katalon getCellText: values this short are used as-is (no truncated-wrapper lookup)
_TRUNCATED = 15
_UPLOAD_MS = 60_000
# Hub stores at most 25 characters (Katalon auto-test_yyyyMMdd_HHmmss fits exactly).
AUTOMATION_SUBMISSION_NAME_LEN = 25


def parse_submission_id_from_text(text: str | None) -> str | None:
    """First UUID in the string, same as Katalon parseSubmissionIdFromText."""
    if text is None or not text.strip():
        return None
    match = _UUID.search(text)
    return match.group(0) if match else None


def _automation_submission_name() -> str:
    """Unique auto-test name within Hub 25-char limit (date + HH + 4 hex in time segment)."""
    date_part = datetime.now().strftime("%Y%m%d")
    hour = datetime.now().strftime("%H")
    segment = f"{hour}{uuid.uuid4().hex[:4]}"
    name = f"auto-test_{date_part}_{segment}"
    if len(name) != AUTOMATION_SUBMISSION_NAME_LEN:
        raise RuntimeError(
            f"automation submission name must be {AUTOMATION_SUBMISSION_NAME_LEN} chars, got {len(name)}: {name!r}"
        )
    return name


class DataSubmissionsListPage(BasePage):
    """List of submissions plus the Create a Data Submission dialog."""

    @property
    def container(self) -> Locator:
        """Filter bar on the list. Visible means the list page has loaded."""
        return self._loc(FILTERS)

    def open(self) -> None:
        """Nav bar → Data Submissions, then wait for the list filters."""
        log.info("Navigate: Data Submissions")
        HeaderPage(self._hub).open_data_submissions()
        self.container.wait_for(state="visible")
        log.info("Data Submissions list page loaded")

    def create_data_submission(
        self,
        sub_type: str,
        data_type: str,
        data_model: str,
        study: str,
    ) -> str:
        """Fill the create dialog, then open the new row from the list.

        Same args as Katalon createDataSubmission (New, metadata only, GC, study).
        Returns 25-char auto-test_yyyyMMdd_HHxxxx name (xxxx = hex). Does not delete the leftover DS.
        """
        self._loc(CREATE_BTN).click()

        # New/Update vs Delete
        if sub_type.lower() == "delete":
            self._loc(SUB_TYPE_DELETE).click()
        else:
            self._loc(SUB_TYPE_NEW).click()

        # Metadata Only vs Metadata and Data Files
        if "only" in (data_type or "").lower():
            self._loc(METADATA_ONLY).click()
        else:
            self._loc(METADATA_FILES).click()

        # Data Commons by exact inner text (GC). Katalon error copy says "Study option".
        self._loc(DATA_COMMONS_DDN).click()
        self._click_option_exact(self._loc(DATA_COMMONS_OPTION), data_model)

        # Study by whitespace-normalized text (autoQA - AutomationQA_Study)
        self._loc(STUDY_DDN).click()
        self._click_study_option(study)

        submission_name = _automation_submission_name()
        log.info("Creating data submission with name %s", submission_name)
        name_box = self._loc(SUBMISSION_NAME)
        name_box.wait_for(state="visible")
        # YAML testid is the MUI wrapper div; Katalon Actions sendKeys into the inner input.
        name_box.locator("input").fill(submission_name)

        self._loc(DIALOG_CREATE).click()
        try:
            self._loc(DIALOG).wait_for(state="hidden")
        except PlaywrightTimeoutError:
            pass
        # Back on the list: Create button is visible again, then filter and open the new row
        self._loc(CREATE_BTN).wait_for(state="visible")
        self._open_created_submission(submission_name)
        return submission_name

    def _click_option_exact(self, options: Locator, text: str) -> None:
        """Click the option whose innerText equals text. Used for Data Commons (GC)."""
        options.first.wait_for(state="visible")
        for i in range(options.count()):
            option = options.nth(i)
            if _inner_text(option).strip() == text:
                option.click()
                return
        raise RuntimeError(f"Study option {text} not found in dropdown.")

    def _click_study_option(self, study: str) -> None:
        """Click the study option after collapsing extra whitespace (Katalon study match)."""
        normalized = " ".join(study.split()).strip()
        options = self._loc(STUDY_OPTION)
        options.first.wait_for(state="visible")
        for i in range(options.count()):
            option = options.nth(i)
            actual = " ".join(_inner_text(option).split()).strip()
            if actual == normalized:
                log.info("Found the study to create DS: '%s'", study)
                option.click()
                return
        raise RuntimeError(f"Study option '{study}' not found in dropdown.")

    def _open_created_submission(self, submission_name: str) -> None:
        """Filter the list by name, require exactly one row, open it, log the UUID.

        Same as Katalon captureAndLogDataSubmissionIdFromList. TC08 only logs the id.
        """
        trimmed = submission_name.strip()
        if not trimmed:
            raise RuntimeError("captureAndLogDataSubmissionIdFromList: submissionName is required.")
        box = self._loc(NAME_FILTER)
        box.wait_for(state="visible")
        rows = self._loc(LIST_ROW)
        before = self._table_fingerprint(rows)
        box.fill(trimmed)
        self._wait_for_table_settled(self._loc(LOADING_ROW), rows, previous=before)
        count = rows.count()
        if count != 1:
            raise RuntimeError(
                f"captureAndLogDataSubmissionIdFromList: expected 1 list row after filtering "
                f"by submission name '{trimmed}', found {count}."
            )
        self._loc(NAME_LINK).first.click()
        self._loc(CHOOSE_FILES).wait_for(state="attached")
        submission_id = parse_submission_id_from_text(self.page.url)
        if submission_id is None:
            raise RuntimeError(
                f"captureAndLogDataSubmissionIdFromList: could not parse submission id "
                f"from URL '{self.page.url}'."
            )
        log.info("Data submission created — name: %s, id: %s", trimmed, submission_id)


class DataSubmissionDetailPage(BasePage):
    """Open submission: metadata upload, Validate, Validation Results table."""

    # Katalon waitForElementNotHasAttribute disabled, 300 seconds
    VALIDATE_MS = 300_000

    def upload_folder(self, tc_name: str, root: Path | None = None) -> None:
        """Choose every top-level TSV in MetadataData/<tcName>, Upload, wait until Uploading is gone.

        Skips expected-ValidationResults (that folder is not top-level *.tsv).
        """
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
        """Click Validate, wait until it is disabled, then until it is enabled again.

        First wait is Katalon waitForElementClickable (30s). Hub disables the button
        while validation runs. Playwright can observe enabled before that disable
        lands, so wait for disabled (started) then enabled (Katalon 5 minutes).
        """
        btn = self._loc(VALIDATE)
        expect(btn).to_be_enabled(timeout=30_000)
        btn.click()
        log.info("Waiting for Validation to finish - waiting up to 5 minutes")
        expect(btn).to_be_disabled(timeout=self.DEFAULT_MS)
        expect(btn).to_be_enabled(timeout=self.VALIDATE_MS)

    def open_validation_results(self) -> None:
        """Validation Results tab, then aggregated/expanded view with filters visible."""
        self._loc(VR_TAB).click()
        self._wait_loading_gone()
        self._ensure_validation_results_expanded()

    def _vr_node_filter_visible(self) -> bool:
        """True when Validation Results node-type filter is on screen (expanded aggregated view)."""
        try:
            self._loc(VR_NODE).first.wait_for(state="visible", timeout=self.PROBE_MS)
            return True
        except PlaywrightTimeoutError:
            return False

    def _ensure_validation_results_expanded(self) -> None:
        """Toggle table-state-switch until node filter is visible (switch is not idempotent)."""
        if self._vr_node_filter_visible():
            return
        for attempt in range(2):
            log.info(
                "Validation Results filters not visible; toggling aggregated/expanded (attempt %s)",
                attempt + 1,
            )
            self._loc(VR_EXPANDED).click()
            self._wait_loading_gone()
            if self._vr_node_filter_visible():
                return
        raise RuntimeError(
            "Validation Results node filter did not become visible after toggling aggregated/expanded"
        )

    def apply_vr_filters(self, node: str, severity: str, issue_type: str) -> None:
        """Node / severity / issue type dropdowns. datafile becomes 'data file'."""
        display_node = node.replace("datafile", "data file") if node == "datafile" else node
        self._wait_loading_gone()
        self._select_li(self._loc(VR_NODE), display_node)
        self._select_li(self._loc(VR_SEVERITY), severity)
        self._wait_loading_gone()
        self._select_li(self._loc(VR_ISSUE), issue_type)
        self._wait_loading_gone()
        rows = self._loc(VR_ROW)
        self._wait_for_table_settled(self._loc(LOADING_ROW), rows)

    def read_vr_rows(self) -> list[tuple[str, str, str]]:
        """Current VR table as (submitted_id, issue_type, severity). Same columns as Katalon."""
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
        """Katalon verifyValidationResultsVsExpectedForTC: one filter+compare per node/severity/issue.

        Empty expected folder logs and returns (Katalon skip). Mismatches are logged,
        then one AssertionError with the count. Utils owns the expected TSV matching.
        """
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
        """Click See details on the VR row matching Submitted Identifier (case-insensitive)."""
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
        """Severity and message pairs from the open error details dialog."""
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
        """Close the error details dialog and wait for it to disappear."""
        self._loc(ERR_CLOSE).click()
        self._loc(ERR_DIALOG).wait_for(state="hidden", timeout=5_000)

    def verify_error_details_for_submitted_id(
        self,
        submitted_identifier: str,
        expected_issues: list[dict[str, str]],
    ) -> None:
        """See details → assert dialog issues → close."""
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
        """Katalon verifyErrorDetailsForSubmittedIdForTC: filters, See details, dialog assert per expected row."""
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
        # Katalon ends with one AggregatedExpanded toggle before verifyValidationResultsVsExpectedForTC.
        self._loc(VR_EXPANDED).click()
        self._wait_loading_gone()
        if errors:
            raise AssertionError(
                f"verifyErrorDetailsForSubmittedIdForTC: {len(errors)} mismatch(es). See log above."
            )

    def _select_li(self, dropdown: Locator, text: str) -> None:
        """Open a MUI dropdown and click the li whose full text equals text."""
        dropdown.first.wait_for(state="visible")
        dropdown.first.click()
        option = self.page.locator("//li").filter(has_text=re.compile(rf"^{re.escape(text)}$"))
        option.first.wait_for(state="visible")
        option.first.click()

    def _wait_loading_gone(self) -> None:
        """Probe for the circular spinner, then wait until it is hidden (Katalon 15s).

        Appearance is optional (spinner may never show). A still-visible spinner
        after 15s fails, same as Katalon waitForElementToDisappear.
        """
        icon = self._loc(LOADING_ICON).first
        try:
            icon.wait_for(state="visible", timeout=self.PROBE_MS)
        except PlaywrightTimeoutError:
            pass
        icon.wait_for(state="hidden", timeout=15_000)

    def _cell_text(self, cells: Locator, index: int) -> str:
        """Katalon getCellText: short values as-is; else truncated-text-wrapper aria-label.

        Hub truncates long ids in the table; the full value is on aria-label.
        """
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


def _inner_text(locator: Locator) -> str:
    """Katalon getAttribute('innerText'), including hidden option text."""
    value = locator.evaluate("el => (el.innerText || '')")
    return value if isinstance(value, str) else ""


def _header_index(names: list[str], wanted: str) -> int:
    """Column index by header label, case-insensitive. -1 if missing."""
    wanted_l = wanted.lower()
    for i, name in enumerate(names):
        if name.lower() == wanted_l:
            return i
    return -1
