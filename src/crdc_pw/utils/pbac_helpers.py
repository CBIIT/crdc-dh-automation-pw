"""PBAC suite orchestration (Katalon utilities/Pbac.groovy).

Home for multi-step PBAC flows that span pages: default permission compares
(TC01–TC05), positive/negative edits and functional permission checks (TC06+).
DOM actions stay on page objects; Excel oracles stay in pbac_sheet.py.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.data_submission_details import CHOOSE_FILES, DataSubmissionDetailPage
from crdc_pw.pages.data_explorer_list import DataExplorerListPage
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.submission_request_form import SubmissionRequestFormPage
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage
from crdc_pw.pages.users import ManageUsersPage, UserProfilePage
from crdc_pw.utils.pbac_sheet import (
    compare_actual,
    list_internal_names_for_scenario,
    output_path,
    write_expected,
)

log = logging.getLogger("crdc_pw.pbac_helpers")

# Locator paths (Katalon Object Repository)
_HOME = "CRDC/NavBar/Home-Btn"
_DS_LOADING = "CRDC/DataSubmissions/Loading-Icon"
_DS_TABLE_ROW = "CRDC/DataSubmissions/DataSubmListTable-Row"
_UNSAVED_SAVE = "CRDC/AILocators/SubmissionRequests/UnsavedChangesDialog/Save-Btn"
_SR_REVIEW_BTN_LEGACY = "CRDC/SubmissionRequest/Review-Btn"
_DS_ACTIONS_SUBMIT = "CRDC/AILocators/DataSubmissions/Detail/Actions/Submit-Btn"
_DS_SUBMIT_DIALOG = "CRDC/AILocators/DataSubmissions/SubmitDialog/Dialog"
# Primary action in the UI is labeled "Yes"; repo YAML uses Confirm-Btn / submit-dialog-confirm-button.
# Katalon also references CRDC/DataSubmissions/SubmitYes-Btn for the same flow.
_DS_SUBMIT_DIALOG_YES = "CRDC/AILocators/DataSubmissions/SubmitDialog/Confirm-Btn"
_DS_CROSS_VALIDATE = "CRDC/AILocators/DataSubmissions/Detail/ValidationControls/CrossValidate-Btn"
_DS_ACTIONS_RELEASE = "CRDC/AILocators/DataSubmissions/Detail/Actions/Release-Btn"
# Katalon data_submission:confirm uses SubmitYes-Btn (//button[.='Yes']) after Release — not ConfirmRelease-Btn (different label).
_DS_ACTIONS_RELEASE_CONFIRMATION_YES = (
    "CRDC/AILocators/DataSubmissions/Detail/Actions/ReleaseConfirmationYes-Btn"
)
_DS_ACTIONS_COMPLETE = "CRDC/AILocators/DataSubmissions/Detail/Actions/Complete-Btn"
_DS_ACTIONS_REJECT = "CRDC/AILocators/DataSubmissions/Detail/Actions/Reject-Btn"
_DS_ACTIONS_WITHDRAW = "CRDC/AILocators/DataSubmissions/Detail/Actions/Withdraw-Btn"
_DS_ACTIONS_ADMIN_SUBMIT = "CRDC/AILocators/DataSubmissions/Detail/Actions/AdminSubmit-Btn"
_DS_ACTIONS_CANCEL = "CRDC/AILocators/DataSubmissions/Detail/Actions/Cancel-Btn"

PROGRAM_TSV = Path("InputFiles/CRDC/MetadataData/PBAC/program.tsv")
PROGRAM_INVALID_TSV = Path("InputFiles/CRDC/MetadataData/PBAC/program_invalid.tsv")

AUTOMATION_STUDY_DS = "ATS - AutoTest-Study"


class _FunctionalHandler(Protocol):
    def __call__(self, hub: Hub, user_role: str, scenario: str) -> bool: ...


def verify_role_defaults_as_admin(hub: Hub, users: ManageUsersPage, role: str) -> None:
    """Phase 1: Admin resets automation user to role defaults and compares UI to Excel.

    Mirrors verifyPbacPermissionDefaults admin branch. Expects hub.role Admin.
    Uses the column named ``role`` in InputFiles/CRDC/PBACPermissions.xlsx.
    """
    users.open()
    log.info("Logged in as: %r and verifying permissions for: %r", hub.role, role)
    users.find_and_edit(role)
    users.reset_permissions(role)
    users.find_and_edit(role)
    users.expand_permission_panels()
    write_expected(role)
    actual = users.read_permission_rows()
    ok = compare_actual(role, actual)
    assert ok, f"{role} defaults mismatch; see {output_path()}"
    log.info("Assert PBAC: %s defaults match PBACPermissions.xlsx", role)


def verify_self_defaults_on_profile(hub: Hub, sheet_column: str) -> None:
    """Phase 2: signed-in role opens Profile and compares checkboxes to Excel *-self column."""
    log.info("Logged in as: %r and verifying permissions for: %r", hub.role, sheet_column)
    profile = UserProfilePage(hub)
    profile.open()
    profile.expand_permission_panels()
    write_expected(sheet_column)
    actual = profile.read_permission_rows()
    ok = compare_actual(sheet_column, actual)
    assert ok, f"{sheet_column} defaults mismatch; see {output_path()}"
    log.info("Assert PBAC: %s defaults match PBACPermissions.xlsx", sheet_column)


def edit_pbac_permissions(
    hub: Hub,
    role: str,
    scenario: Literal["positive", "negative"],
) -> None:
    """Katalon editPbacPermissions: Admin edits PBAC for role, then writes expected sheet."""
    if scenario == "negative":
        raise NotImplementedError(
            "edit_pbac_permissions negative scenario is reserved for TC11+ (uncheck path)."
        )
    if hub.role != "Admin":
        raise AssertionError(f"edit_pbac_permissions requires Admin; hub.role is {hub.role!r}")
    users = ManageUsersPage(hub)
    users.open()
    users.apply_positive_permission_edit(role)
    key = f"{role}-{scenario}"
    write_expected(key)
    log.info("Wrote expected PBAC sheet %r after positive edit", key)


def verify_permissions_functional(
    hub: Hub,
    user_role: str,
    scenario: Literal["positive", "negative"],
) -> None:
    """Katalon verifyPermissionsFunctional: iterate output sheet keys, handler or skip."""
    if scenario == "negative":
        raise NotImplementedError(
            "verify_permissions_functional for negative scenario is reserved for TC11+."
        )
    keys = list_internal_names_for_scenario(user_role, scenario)
    log.info(
        "Permissions to verify for %r role for %r scenario: %s",
        user_role,
        scenario,
        keys,
    )
    for perm in keys:
        handler = _PERMISSION_FUNCTIONAL.get(perm)
        if handler is None:
            log.info(
                "Skipping '%s' — email/notification permission (see NotificationEmails suite).",
                perm,
            )
            continue
        try:
            result = handler(hub, user_role, scenario)
        except Exception as exc:
            pytest.fail(f"[ERROR] Exception during permission {perm!r}: {exc}")
        assert result, f"[FAIL] Unexpected result for permission {perm!r} in positive scenario."
        log.info("[PASS] %r accessible as expected.", perm)


# --- Small helpers (Katalon SubmissionRequest.clickHome, loading waits) ---


def _pbac_click_home(hub: Hub) -> None:
    hub.page.locator(hub.locators.get(_HOME)).click()


def _wait_ds_loading_gone(hub: Hub) -> None:
    DataSubmissionDetailPage(hub).wait_loading_spinner_gone()


def _open_data_submissions_list_settled(hub: Hub) -> None:
    """Nav → Data Submissions, then CircularProgress gone + generic table loading row settled.

    Matches the race fix for ``data_submission:view``: Katalon only waits on Loading-Icon, but the
    list can still show a transient permission placeholder until the table loading row clears.
    """
    HeaderPage(hub).open_data_submissions()
    _wait_ds_loading_gone(hub)
    DataSubmissionsListPage(hub).wait_for_list_table_settled()


def _open_submission_requests_list_settled(hub: Hub) -> None:
    """Nav → Submission Requests list and wait for generic-table loading row to finish.

    PBAC must not use ``_wait_ds_loading_gone`` here: that waits on the **Data Submissions**
    loading icon and does not synchronize the SR list. Reading ``tbody tr`` too early can
    look like a single permission-denied row (flake).
    """
    SubmissionRequestsListPage(hub).open()


def _profile_name(hub: Hub) -> str:
    return HeaderPage(hub).username()


def _sr_list_table_rows(hub: Hub):
    return hub.page.locator(hub.locators.get("CRDC/SubmissionRequest/SubmReqListTable-Row"))


def _ds_list_table_rows(hub: Hub):
    return hub.page.locator(hub.locators.get(_DS_TABLE_ROW))


def _ds_or_explorer_list_has_positive_rows(rows) -> bool:
    """True when the list shows real data rows (not the single-row permission-denied message)."""
    n = rows.count()
    if n == 0:
        return False
    if n == 1:
        text = rows.first.inner_text() or ""
        if "do not have the appropriate permissions" in text:
            return False
    return n > 0


def _prepare_unique_program_tsv() -> Path:
    """Same uniqueness idea as Katalon prepareUniqueMetadataAndUpload (program_acronym)."""
    root = repo_root()
    src = root / PROGRAM_TSV
    if not src.is_file():
        raise FileNotFoundError(f"PBAC metadata driver missing: {src}")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = src.with_name(src.stem + f"_mod_{ts}" + src.suffix)
    lines = src.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise RuntimeError(f"Unexpected empty TSV: {src}")
    header = lines[0]
    headers = header.split("\t")
    try:
        idx = headers.index("program_acronym")
    except ValueError as exc:
        raise RuntimeError(f"program_acronym column missing in {src}") from exc
    data = lines[1].split("\t")
    if len(data) > idx:
        data[idx] = data[idx] + "_" + ts
    dest.write_text(header + "\n" + "\t".join(data) + "\n", encoding="utf-8")
    return dest


def _upload_metadata_file_on_detail(hub: Hub, absolute_path: Path) -> None:
    page = hub.page
    path = absolute_path.resolve()
    log.info("DS PBAC: uploading metadata file %s", path)
    choose = page.locator(hub.locators.get("CRDC/DataSubmissions/ChooseFiles-Btn"))
    choose.wait_for(state="attached")
    choose.set_input_files(str(path))
    page.locator(hub.locators.get("CRDC/DataSubmissions/Upload-Btn")).click()
    log.info("DS PBAC: waiting for Uploading indicator to clear")
    uploading = page.locator(hub.locators.get("CRDC/DataSubmissions/Uploading-Txt")).first
    try:
        uploading.wait_for(state="visible", timeout=2_000)
    except Exception:
        pass
    uploading.wait_for(state="hidden", timeout=120_000)
    log.info("DS PBAC: upload finished; waiting for Validate to enable")
    validate_btn = page.locator(hub.locators.get("CRDC/DataSubmissions/Validate-Btn"))
    validate_btn.wait_for(state="visible")
    # Katalon waits until Validate enables after ingest
    deadline = datetime.now().timestamp() + 120
    while datetime.now().timestamp() < deadline:
        if validate_btn.is_enabled():
            log.info("DS PBAC: Validate is enabled after upload")
            return
        page.wait_for_timeout(300)
    raise AssertionError("Validate did not become enabled after metadata upload")


def _click_ds_submit_dialog_yes(hub: Hub) -> None:
    """Submit → wait for dialog, click Yes (Confirm-Btn), wait for dialog to close.

    Do not wait for the Yes control to become ``hidden`` after click: the dialog often
    unmounts the button immediately, which can detach the node and fail Playwright's
    hidden wait even when submit succeeded.
    """
    page = hub.page
    dialog = page.locator(hub.locators.get(_DS_SUBMIT_DIALOG))
    yes_btn = page.locator(hub.locators.get(_DS_SUBMIT_DIALOG_YES)).first
    log.info("DS PBAC: waiting for submit dialog (data-testid=submit-dialog)")
    dialog.wait_for(state="visible", timeout=30_000)
    expect(yes_btn).to_be_visible(timeout=30_000)
    expect(yes_btn).to_be_enabled(timeout=30_000)
    log.info("DS PBAC: clicking submit dialog Yes (Confirm-Btn)")
    yes_btn.click()
    log.info("DS PBAC: waiting for submit dialog to close")
    dialog.wait_for(state="hidden", timeout=30_000)


def _click_ds_release_confirmation_yes(hub: Hub) -> None:
    """Katalon Pbac data_submission:confirm: click Release then ``SubmitYes-Btn`` (//button[.='Yes']).

    The repo's ``ConfirmRelease-Btn`` targets text ``Confirm Release``, not the Yes/No pair.
    ``ReleaseConfirmationYes-Btn`` matches the primary ``Yes`` on the release confirmation dialog.
    """
    page = hub.page
    yes_btn = page.locator(hub.locators.get(_DS_ACTIONS_RELEASE_CONFIRMATION_YES)).first
    log.info("DS PBAC (confirm): waiting for Release confirmation Yes button")
    expect(yes_btn).to_be_visible(timeout=30_000)
    expect(yes_btn).to_be_enabled(timeout=30_000)
    log.info("DS PBAC (confirm): clicking Yes (Katalon SubmitYes-Btn parity)")
    yes_btn.click()


def _functional_submission_request_view(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying SR View...")
    try:
        hub.page.wait_for_timeout(1_000)
        _pbac_click_home(hub)
        _open_submission_requests_list_settled(hub)
        rows = _sr_list_table_rows(hub)
        n = rows.count()
        if n == 1:
            text = rows.first.inner_text() or ""
            if "do not have the appropriate permissions" in text:
                log.info(
                    "SR list shows permission-denied empty state (single row with that message); "
                    "positive view check fails."
                )
                return False
        log.info("Number of rows in SR list found: %s", n)
        if n > 1:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            log.info(
                "Capturing screenshot: SR list shows data rows instead of permission-denied message (%s)",
                ts,
            )
            hub.page.screenshot(full_page=True, path=str(repo_root() / f"reports/PBAC_FAIL_submission_request_view_SR_list_{ts}.png"))
        return n > 0
    except Exception as exc:
        log.info("Error verifying permission - submission_request:view -> %s", exc)
        return False


def _functional_submission_request_create(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying SR Create...")
    try:
        _pbac_click_home(hub)
        _open_submission_requests_list_settled(hub)
        start = SubmissionRequestsListPage(hub)._start_button()
        return start.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - submission_request:create -> %s", exc)
        return False


def _functional_submission_request_submit(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying SR Submit...")
    try:
        _pbac_click_home(hub)
        _open_submission_requests_list_settled(hub)
        sr_list = SubmissionRequestsListPage(hub)
        start = sr_list._start_button()
        if not start.is_visible():
            return False
        form = SubmissionRequestFormPage(hub)

        # SR resume flow
        sr_list.start_new_submission_request()
        # Save is disabled until the form is dirty; fill PI so Save can be clicked.
        form.enter_principal_investigator_info(2)
        form.click_save()
        HeaderPage(hub).open_submission_requests()
        # Leaving with incomplete Section A opens the unsaved-changes dialog; Save there to keep the draft.
        # Locator is scoped to [role='dialog']; do not use .first — plain //button[.='Save'] would match the form Save too.
        save_btn = hub.page.locator(hub.locators.get(_UNSAVED_SAVE))
        try:
            save_btn.wait_for(state="visible", timeout=5_000)
        except PlaywrightTimeoutError:
            pass
        else:
            log.info("Unsaved changes dialog present; clicking Save")
            save_btn.click()
            save_btn.wait_for(state="hidden", timeout=10_000)
        # }
        sr_list.container.wait_for(state="visible", timeout=15_000)
        sr_list.wait_for_list_table_settled()

        name = _profile_name(hub)
        sr_list.apply_submission_requests_list_filters(
            {
                "submitterName": name,
                "program": "",
                "study": "",
                "status": "In Progress",
            }
        )
        resume = hub.page.get_by_role("button", name=re.compile(r"^Resume$", re.I)).first
        sr_list_resume = resume.is_visible()

        # SR create/submit flow
        sr_list.start_new_submission_request()
        # CRDCDH-3948-style fill (replaces chained enter* / Save / Next in Groovy).
        form.fill_submission_request_all_sections(
            2,
            "Other",
            6,
            1,
            1,
            "Open",
            "Yes",
            "Cholangiocarcinoma",
            "Homo",
            1,
            "genomics",
            "proteomics",
            5,
            6,
            1,
            1,
        )
        submit = hub.page.locator(hub.locators.get("CRDC/SubmissionRequest/Submit-Btn")).first
        submit.wait_for(state="visible", timeout=40_000)
        sr_submit_exists = submit.is_visible()
        return bool(sr_list_resume and sr_submit_exists)
    except Exception as exc:
        log.info("Error verifying permission - submission_request:submit -> %s", exc)
        return False


def _functional_submission_request_review(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying SR Review...")
    try:
        hub.page.wait_for_timeout(1_000)
        _pbac_click_home(hub)
        _open_submission_requests_list_settled(hub)
        sr_list = SubmissionRequestsListPage(hub)
        sr_list.apply_submission_requests_list_filters(
            {
                "submitterName": "",
                "program": "",
                "study": "",
                "status": "Submitted, In Review",
            }
        )
        review_row = hub.page.locator(hub.locators.get(_SR_REVIEW_BTN_LEGACY)).first
        if not review_row.is_visible():
            return False
        review_row.click()
        form = SubmissionRequestFormPage(hub)
        form.click_review_progress_bar()
        approve = hub.page.locator(
            hub.locators.get("CRDC/AILocators/SubmissionRequests/Form/Navigation/Approve-Btn")
        ).first
        reject = hub.page.locator(
            hub.locators.get("CRDC/AILocators/SubmissionRequests/Form/Navigation/Reject-Btn")
        ).first
        inquire = hub.page.locator(
            hub.locators.get("CRDC/AILocators/SubmissionRequests/Form/Navigation/Inquire-Btn")
        ).first
        return approve.is_visible() and reject.is_visible() and inquire.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - submission_request:review -> %s", exc)
        return False


def _functional_submission_request_cancel(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying SR Cancel...")
    try:
        _pbac_click_home(hub)
        _open_submission_requests_list_settled(hub)
        name = _profile_name(hub)
        sr_list = SubmissionRequestsListPage(hub)
        sr_list.apply_submission_requests_list_filters(
            {
                "submitterName": name,
                "program": "",
                "study": "",
                "status": "In Progress",
            }
        )
        cancel = hub.page.locator(hub.locators.get("CRDC/SubmissionRequest/Cancel-Btn")).first
        return cancel.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - submission_request:cancel -> %s", exc)
        return False


def _functional_submission_request_reopen(
    hub: Hub, _user_role: str, scenario: str
) -> bool:
    log.info("Verifying SR Reopen...")
    try:
        hub.page.wait_for_timeout(1_000)
        _pbac_click_home(hub)
        _open_submission_requests_list_settled(hub)
        sr_list = SubmissionRequestsListPage(hub)
        sr_list.apply_submission_requests_list_filters(
            {
                "submitterName": "",
                "program": "",
                "study": "",
                "status": "Approved",
            }
        )
        rows = _sr_list_table_rows(hub)
        n = rows.count()
        no_perm = (
            n == 1
            and "do not have the appropriate permissions" in (rows.first.inner_text() or "")
        )
        no_approved = n == 0 or no_perm
        if scenario.lower() == "positive" and no_approved:
            pytest.fail(
                "Approved submission required for reopen PBAC check; seed QA with at least "
                "one Approved SR visible to this role."
            )
        reopen = hub.page.locator(hub.locators.get("CRDC/AILocators/SubmissionRequests/List/Reopen-Btn"))
        reopen_present = reopen.first.is_visible() if reopen.count() else False
        log.info("SR Reopen list rows: %s, Reopen control present: %s", n, reopen_present)
        return reopen_present
    except Exception as exc:
        log.info("Error verifying permission - submission_request:reopen -> %s", exc)
        return False


def _functional_data_submission_view(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying DS View...")
    try:
        _pbac_click_home(hub)
        _open_data_submissions_list_settled(hub)
        rows_ds = _ds_list_table_rows(hub)
        if rows_ds.count() == 1 and "do not have the appropriate permissions" in (
            rows_ds.first.inner_text() or ""
        ):
            log.info("The Data Submissions empty table message is displayed")
        n_ds = rows_ds.count()
        log.info("Number of rows in Data Submission list found: %s", n_ds)

        _pbac_click_home(hub)
        DataExplorerListPage(hub).open_settled()
        rows_de = _ds_list_table_rows(hub)
        if rows_de.count() == 1 and "do not have the appropriate permissions" in (
            rows_de.first.inner_text() or ""
        ):
            log.info("The Data Explorer empty table message is displayed")
        n_de = rows_de.count()
        log.info("Number of rows in Data Explorer list found: %s", n_de)

        ds_ok = _ds_or_explorer_list_has_positive_rows(rows_ds)
        de_ok = _ds_or_explorer_list_has_positive_rows(rows_de)
        return ds_ok and de_ok and n_ds > 0 and n_de > 0
    except Exception as exc:
        log.info("Error verifying permission - data_submission:view -> %s", exc)
        return False


def _functional_data_submission_create(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying DS Create...")
    try:
        _pbac_click_home(hub)
        _open_data_submissions_list_settled(hub)
        create = hub.page.locator(
            hub.locators.get("CRDC/AILocators/DataSubmissions/List/Table/CreateDataSubmission-Btn")
        )
        data_submission_create = create.first.is_visible()
        HeaderPage(hub).open_user_menu()
        api = hub.page.locator(hub.locators.get("CRDC/AILocators/Global/Header/Desktop/APIToken-Btn"))
        api_token = api.first.is_visible()
        _pbac_click_home(hub)
        return data_submission_create and api_token
    except Exception as exc:
        log.info("Error verifying permission - data_submission:create -> %s", exc)
        return False


def _functional_data_submission_cancel(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying DS Cancel...")
    try:
        _pbac_click_home(hub)
        _open_data_submissions_list_settled(hub)
        create = hub.page.locator(
            hub.locators.get("CRDC/AILocators/DataSubmissions/List/Table/CreateDataSubmission-Btn")
        )
        if not create.first.is_visible():
            return False
        ds_list = DataSubmissionsListPage(hub)
        ds_list.create_data_submission(
            "New/Update",
            "metadata only",
            "GC",
            AUTOMATION_STUDY_DS,
        )
        hub.page.locator(hub.locators.get("CRDC/DataSubmissions/DataSubmissionName-Link")).first.click()
        hub.page.locator(hub.locators.get(CHOOSE_FILES)).wait_for(state="attached")
        _wait_ds_loading_gone(hub)
        cancel = hub.page.locator(hub.locators.get(_DS_ACTIONS_CANCEL)).first
        return cancel.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - data_submission:cancel -> %s", exc)
        return False


def _functional_data_submission_review(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying DS Review...")
    try:
        _pbac_click_home(hub)
        _open_data_submissions_list_settled(hub)
        create = hub.page.locator(
            hub.locators.get("CRDC/AILocators/DataSubmissions/List/Table/CreateDataSubmission-Btn")
        )
        if not create.first.is_visible():
            return False
        ds_list = DataSubmissionsListPage(hub)
        ds_list.create_data_submission(
            "New/Update",
            "metadata only",
            "GC",
            AUTOMATION_STUDY_DS,
        )
        hub.page.locator(hub.locators.get("CRDC/DataSubmissions/DataSubmissionName-Link")).first.click()
        detail = DataSubmissionDetailPage(hub)
        log.info("DS PBAC (review): waiting for detail loading spinner")
        detail.wait_loading_spinner_gone()
        temp = _prepare_unique_program_tsv()
        try:
            _upload_metadata_file_on_detail(hub, temp)
        finally:
            temp.unlink(missing_ok=True)
        log.info("DS PBAC (review): starting validation")
        detail.click_validate()
        log.info("DS PBAC (review): validation finished")
        page = hub.page
        submit = page.locator(hub.locators.get(_DS_ACTIONS_SUBMIT)).first
        log.info("DS PBAC (review): waiting for Submit action")
        submit.wait_for(state="visible", timeout=30_000)
        submit.click()
        _click_ds_submit_dialog_yes(hub)
        detail.wait_loading_spinner_gone()
        release = page.locator(hub.locators.get(_DS_ACTIONS_RELEASE)).first
        reject = page.locator(hub.locators.get(_DS_ACTIONS_REJECT)).first
        withdraw = page.locator(hub.locators.get(_DS_ACTIONS_WITHDRAW)).first
        return release.is_visible() and reject.is_visible() and withdraw.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - data_submission:review -> %s", exc)
        return False


def _functional_data_submission_admin_submit(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying DS Admin Submit...")
    try:
        _pbac_click_home(hub)
        _open_data_submissions_list_settled(hub)
        create = hub.page.locator(
            hub.locators.get("CRDC/AILocators/DataSubmissions/List/Table/CreateDataSubmission-Btn")
        )
        if not create.first.is_visible():
            return False
        ds_list = DataSubmissionsListPage(hub)
        ds_list.create_data_submission(
            "New/Update",
            "metadata only",
            "GC",
            AUTOMATION_STUDY_DS,
        )
        hub.page.locator(hub.locators.get("CRDC/DataSubmissions/DataSubmissionName-Link")).first.click()
        detail = DataSubmissionDetailPage(hub)
        detail.wait_loading_spinner_gone()
        root = repo_root()
        invalid = root / PROGRAM_INVALID_TSV
        if not invalid.is_file():
            raise FileNotFoundError(invalid)
        _upload_metadata_file_on_detail(hub, invalid)
        detail.click_validate()
        admin_submit = hub.page.locator(hub.locators.get(_DS_ACTIONS_ADMIN_SUBMIT)).first
        try:
            admin_submit.wait_for(state="visible", timeout=30_000)
        except Exception:
            return False
        return admin_submit.is_enabled()
    except Exception as exc:
        log.info("Error verifying permission - data_submission:admin_submit -> %s", exc)
        return False


def _functional_data_submission_confirm(hub: Hub, user_role: str, scenario: str) -> bool:
    log.info("Verifying DS Confirm...")
    try:
        _pbac_click_home(hub)
        _open_data_submissions_list_settled(hub)
        create = hub.page.locator(
            hub.locators.get("CRDC/AILocators/DataSubmissions/List/Table/CreateDataSubmission-Btn")
        )
        if not create.first.is_visible():
            return False
        ds_list = DataSubmissionsListPage(hub)
        ds_list.create_data_submission(
            "New/Update",
            "metadata only",
            "GC",
            AUTOMATION_STUDY_DS,
        )
        hub.page.locator(hub.locators.get("CRDC/DataSubmissions/DataSubmissionName-Link")).first.click()
        detail = DataSubmissionDetailPage(hub)
        log.info("DS PBAC (confirm): waiting for detail loading spinner")
        detail.wait_loading_spinner_gone()
        temp = _prepare_unique_program_tsv()
        try:
            _upload_metadata_file_on_detail(hub, temp)
        finally:
            temp.unlink(missing_ok=True)
        log.info("DS PBAC (confirm): starting validation")
        detail.click_validate()
        log.info("DS PBAC (confirm): validation finished")
        page = hub.page
        submit = page.locator(hub.locators.get(_DS_ACTIONS_SUBMIT)).first
        log.info("DS PBAC (confirm): waiting for Submit action")
        submit.wait_for(state="visible", timeout=30_000)
        submit.click()
        _click_ds_submit_dialog_yes(hub)
        detail.wait_loading_spinner_gone()
        if user_role.lower() == "submitter" and scenario.lower() == "negative":
            cross = page.locator(hub.locators.get(_DS_CROSS_VALIDATE)).first
            release = page.locator(hub.locators.get(_DS_ACTIONS_RELEASE)).first
            complete = page.locator(hub.locators.get(_DS_ACTIONS_COMPLETE)).first
            return cross.is_visible() or release.is_visible() or complete.is_visible()
        page.locator(hub.locators.get(_DS_CROSS_VALIDATE)).first.click()
        log.info("DS PBAC (confirm): waiting for Release action")
        page.locator(hub.locators.get(_DS_ACTIONS_RELEASE)).first.wait_for(state="visible", timeout=30_000)
        page.locator(hub.locators.get(_DS_ACTIONS_RELEASE)).first.click()
        _click_ds_release_confirmation_yes(hub)
        detail.wait_loading_spinner_gone()
        complete = page.locator(hub.locators.get(_DS_ACTIONS_COMPLETE)).first
        reject = page.locator(hub.locators.get(_DS_ACTIONS_REJECT)).first
        return complete.is_visible() and reject.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - data_submission:confirm -> %s", exc)
        return False


def _functional_program_manage(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Manage Programs...")
    try:
        _pbac_click_home(hub)
        HeaderPage(hub).open_user_menu()
        return hub.page.locator(hub.locators.get("CRDC/NavBar/ManagePrograms-Btn")).first.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - program:manage -> %s", exc)
        return False


def _functional_study_manage(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Manage Studies...")
    try:
        _pbac_click_home(hub)
        HeaderPage(hub).open_user_menu()
        return hub.page.locator(hub.locators.get("CRDC/NavBar/ManageStudies-Btn")).first.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - study:manage -> %s", exc)
        return False


def _functional_institution_manage(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Manage Institutions...")
    try:
        _pbac_click_home(hub)
        HeaderPage(hub).open_user_menu()
        return hub.page.locator(hub.locators.get("CRDC/NavBar/ManageInstitutions-Btn")).first.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - institution:manage -> %s", exc)
        return False


def _functional_user_manage(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Manage Users...")
    try:
        _pbac_click_home(hub)
        HeaderPage(hub).open_user_menu()
        return hub.page.locator(hub.locators.get("CRDC/NavBar/ManageUsers-Btn")).first.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - user:manage -> %s", exc)
        return False


def _functional_dashboard_view(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Operation Dashboard...")
    try:
        _pbac_click_home(hub)
        HeaderPage(hub).open_user_menu()
        return hub.page.locator(hub.locators.get("CRDC/NavBar/OperationDashboard-Btn")).first.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - dashboard:view -> %s", exc)
        return False


def _functional_access_request(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Request Access...")
    try:
        _pbac_click_home(hub)
        HeaderPage(hub).open_user_menu()
        hub.page.locator(hub.locators.get("CRDC/AILocators/Global/Header/Desktop/UserProfile-Link")).click()
        return hub.page.locator(hub.locators.get("CRDC/ManageUsers/RequestAccess-Btn")).first.is_visible()
    except Exception as exc:
        log.info("Error verifying permission - access:request -> %s", exc)
        return False


_PERMISSION_FUNCTIONAL: dict[str, _FunctionalHandler] = {
    "submission_request:view": _functional_submission_request_view,
    "submission_request:create": _functional_submission_request_create,
    "submission_request:submit": _functional_submission_request_submit,
    "submission_request:review": _functional_submission_request_review,
    "submission_request:cancel": _functional_submission_request_cancel,
    "submission_request:reopen": _functional_submission_request_reopen,
    "data_submission:view": _functional_data_submission_view,
    "data_submission:create": _functional_data_submission_create,
    "data_submission:cancel": _functional_data_submission_cancel,
    "data_submission:review": _functional_data_submission_review,
    "data_submission:admin_submit": _functional_data_submission_admin_submit,
    "data_submission:confirm": _functional_data_submission_confirm,
    "program:manage": _functional_program_manage,
    "study:manage": _functional_study_manage,
    "institution:manage": _functional_institution_manage,
    "user:manage": _functional_user_manage,
    "dashboard:view": _functional_dashboard_view,
    "access:request": _functional_access_request,
}
