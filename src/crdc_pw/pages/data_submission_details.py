"""Data Submission detail: upload, validate, Validation Results, error-details dialog.

Construct DataSubmissionDetailPage(hub) after opening a submission from the list.
TSV oracles stay in utils/validation_results.py.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Mapping

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.base import BasePage
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

log = logging.getLogger("crdc_pw.data_submission_details")

# QA automation DS create + summary header oracles (Katalon utilities.DataSubmissions static defaults)
DS_AUTOMATION_STUDY_CREATE = "autoQA - AutomationQA_Study"
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
LOADING_ROW = "CRDC/AILocators/GenericTable/LoadingRow"

ERR_DIALOG = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/Dialog"
ERR_CLOSE = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/Close-Btn"
ERR_SEVERITY = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/IssueSeverity-Lbl"
ERR_MESSAGE = "CRDC/AILocators/DataSubmissions/ErrorDetailsDialog/IssueMessage-Lbl"

SUMMARY_SUBMISSION_NAME = "CRDC/AILocators/DataSubmissions/Detail/Summary/SubmissionName-Lbl"
SUMMARY_COLLABORATORS_BTN = "CRDC/AILocators/DataSubmissions/Detail/Summary/Collaborators-Btn"
SUMMARY_HEADER_ROOT = "CRDC/AILocators/DataSubmissions/Detail/Summary/SummaryHeader-Root"
_TRUNCATED = 15
_UPLOAD_MS = 60_000


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
    def collaborators_button(self) -> Locator:
        """Collaborators control on the summary header (tooltip hover target)."""
        return self._loc(SUMMARY_COLLABORATORS_BTN)

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

    def open_validation_results(self) -> None:
        """Validation Results tab, then aggregated/expanded view with filters visible."""
        self._loc(VR_TAB).click()
        self._wait_loading_gone()
        self._ensure_validation_results_expanded()

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
            self._wait_loading_gone()
            if self._vr_node_filter_visible():
                return
        raise RuntimeError(
            "Validation Results node filter did not become visible after toggling aggregated/expanded"
        )

    def apply_vr_filters(self, node: str, severity: str, issue_type: str) -> None:
        """Set node, severity, and issue type filters and wait for the Validation Results table to settle."""
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
        self._wait_loading_gone()
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

    def wait_loading_spinner_gone(self) -> None:
        """Wait until the Hub circular progress overlay hides (lists and detail)."""
        self._wait_loading_gone()

    def _wait_loading_gone(self) -> None:
        icon = self._loc(LOADING_ICON).first
        try:
            icon.wait_for(state="visible", timeout=self.PROBE_MS)
        except PlaywrightTimeoutError:
            pass
        icon.wait_for(state="hidden", timeout=15_000)

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
