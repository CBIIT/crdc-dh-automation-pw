"""Data Submissions list and create dialog.

Tests construct DataSubmissionsListPage(hub), then open() and create_data_submission(...).
Upload / validate / VR live on DataSubmissionDetailPage in data_submission_details.py.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime

from playwright.sync_api import Locator
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage
from crdc_pw.pages.data_submission_details import CHOOSE_FILES
from crdc_pw.pages.header import HeaderPage

log = logging.getLogger("crdc_pw.data_submissions_list")

CREATE_BTN = "CRDC/AILocators/DataSubmissions/List/Table/CreateDataSubmission-Btn"
FILTERS = "CRDC/AILocators/DataSubmissions/List/Filters/Filters-Container"
LIST_ROW = "CRDC/AILocators/GenericTable/TableRow"
NAME_FILTER = "CRDC/AILocators/DataSubmissions/List/Filters/SubmissionName-TxtBx"
NAME_LINK = "CRDC/DataSubmissions/DataSubmissionName-Link"

SUB_TYPE_DELETE = "CRDC/DataSubmissions/Create/SubTypeDelete-Btn"
SUB_TYPE_NEW = "CRDC/DataSubmissions/Create/SubTypeNewUpdate-Btn"
METADATA_ONLY = "CRDC/DataSubmissions/Create/MetadataOnly-Btn"
METADATA_FILES = "CRDC/DataSubmissions/Create/MetadataDataFiles-Btn"
DATA_COMMONS_DDN = "CRDC/DataSubmissions/Create/DataCommons-Ddn"
DATA_COMMONS_OPTION = "CRDC/DataSubmissions/Create/DataCommonsDdn-Option"
STUDY_DDN = "CRDC/DataSubmissions/Create/Study-Ddn"
STUDY_OPTION = "CRDC/DataSubmissions/Create/StudyDdn-Option"
SUBMISSION_NAME = "CRDC/AILocators/DataSubmissions/CreateDialog/SubmissionName-TxtBx"
DIALOG_CREATE = "CRDC/AILocators/DataSubmissions/CreateDialog/Create-Btn"
DIALOG = "CRDC/AILocators/DataSubmissions/CreateDialog/Dialog"

_UUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
# Hub stores at most this many characters of the submission name (parallel-safe auto-test names use all 25).
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


def _inner_text(locator: Locator) -> str:
    """Katalon getAttribute('innerText'), including hidden option text."""
    value = locator.evaluate("el => (el.innerText || '')")
    return value if isinstance(value, str) else ""


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

    def wait_for_list_table_settled(self) -> None:
        """Wait until the generic-table loading row is gone (same pattern as SubmissionRequests list).

        PBAC and other flows call ``wait_loading_spinner_gone`` then read ``tbody/tr``; the table
        can still show a transient placeholder row until the loading row disappears.
        """
        self.container.wait_for(state="visible")
        self.wait_for_generic_table_settled(self._loc(LIST_ROW))

    def table_data_rows(self) -> Locator:
        """Generic table body rows (PBAC ``data_submission:view`` parity with Katalon list row)."""
        return self._loc(LIST_ROW)

    def is_create_visible(self) -> bool:
        """True if the list shows Create a Data Submission (PBAC ``data_submission:create`` gate)."""
        return self._loc(CREATE_BTN).first.is_visible()

    def create_data_submission(
        self,
        sub_type: str,
        data_type: str,
        data_model: str,
        study: str,
    ) -> str:
        """Fill the create dialog, filter the list, open the new submission on the upload-activity page, and return its 25-char auto-test name (Katalon createDataSubmission args)."""
        self._loc(CREATE_BTN).click()

        if sub_type.lower() == "delete":
            self._loc(SUB_TYPE_DELETE).click()
        else:
            self._loc(SUB_TYPE_NEW).click()

        if "only" in (data_type or "").lower():
            self._loc(METADATA_ONLY).click()
        else:
            self._loc(METADATA_FILES).click()

        self._loc(DATA_COMMONS_DDN).click()
        self._click_option_exact(self._loc(DATA_COMMONS_OPTION), data_model)

        self._loc(STUDY_DDN).click()
        self._click_study_option(study)

        submission_name = _automation_submission_name()
        log.info("Creating data submission with name %s", submission_name)
        name_box = self._loc(SUBMISSION_NAME)
        name_box.wait_for(state="visible")
        name_box.locator("input").fill(submission_name)

        self._loc(DIALOG_CREATE).click()
        try:
            self._loc(DIALOG).wait_for(state="hidden")
        except PlaywrightTimeoutError:
            pass
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
        """Filter the list by name, require exactly one row, open it, log the UUID."""
        trimmed = submission_name.strip()
        if not trimmed:
            raise RuntimeError("captureAndLogDataSubmissionIdFromList: submissionName is required.")
        box = self._loc(NAME_FILTER)
        box.wait_for(state="visible")
        rows = self._loc(LIST_ROW)
        before = self._table_fingerprint(rows)
        box.fill(trimmed)
        self.wait_for_generic_table_settled(rows, previous=before)
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
