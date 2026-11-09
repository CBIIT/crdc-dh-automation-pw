"""PBAC suite orchestration (Katalon utilities/Pbac.groovy).

Orchestrates TC01–TC05 defaults and TC06+ functional permission checks: navigation
order, Excel oracles via ``pbac_sheet``, logging, and ``pytest`` assertions.
Handlers delegate all DOM to page objects under ``crdc_pw.pages``; do not add new
``hub.page.locator`` calls here for functional checks.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

import pytest

from crdc_pw.hub import Hub
from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.data_submission_details import DataSubmissionDetailPage
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
    HeaderPage(hub).go_home()


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


def _functional_submission_request_view(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying SR View...")
    try:
        hub.page.wait_for_timeout(1_000)
        _pbac_click_home(hub)
        _open_submission_requests_list_settled(hub)
        rows = SubmissionRequestsListPage(hub).table_data_rows()
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
        return SubmissionRequestsListPage(hub).is_start_submission_request_visible()
    except Exception as exc:
        log.info("Error verifying permission - submission_request:create -> %s", exc)
        return False


def _functional_submission_request_submit(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying SR Submit...")
    try:
        _pbac_click_home(hub)
        _open_submission_requests_list_settled(hub)
        sr_list = SubmissionRequestsListPage(hub)
        if not sr_list.is_start_submission_request_visible():
            return False
        form = SubmissionRequestFormPage(hub)

        # SR resume flow
        sr_list.start_new_submission_request()
        form.assert_status("NEW")
        form.enter_principal_investigator_info(2)
        # CRDCDH-3948: prefilled PI values may be unchanged; explicitly edit before Save.
        form.set_pi_address(f"PBAC draft address {datetime.now():%Y%m%d%H%M%S%f}")
        form.assert_save_enabled()
        form.click_save()
        form.assert_status("IN PROGRESS")
        sr_list.return_to_list_after_partial_save()

        name = _profile_name(hub)
        sr_list.apply_submission_requests_list_filters(
            {
                "submitterName": name,
                "program": "",
                "study": "",
                "status": "In Progress",
            }
        )
        sr_list_resume = sr_list.is_resume_button_visible()

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
        sr_submit_exists = form.is_submit_button_visible()
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
        if not sr_list.is_review_button_visible_on_list():
            return False
        sr_list.click_review_on_first_matching_row()
        form = SubmissionRequestFormPage(hub)
        form.click_review_progress_bar()
        return form.are_review_decision_buttons_visible()
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
        return sr_list.is_cancel_button_visible_on_first_row()
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
        rows = sr_list.table_data_rows()
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
        reopen_present = sr_list.is_reopen_button_visible()
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
        rows_ds = DataSubmissionsListPage(hub).table_data_rows()
        if rows_ds.count() == 1 and "do not have the appropriate permissions" in (
            rows_ds.first.inner_text() or ""
        ):
            log.info("The Data Submissions empty table message is displayed")
        n_ds = rows_ds.count()
        log.info("Number of rows in Data Submission list found: %s", n_ds)

        ds_ok = _ds_or_explorer_list_has_positive_rows(rows_ds)
        _pbac_click_home(hub)
        explorer = DataExplorerListPage(hub)
        explorer.open_settled()
        rows_de = explorer.table_data_rows()
        if rows_de.count() == 1 and "do not have the appropriate permissions" in (
            rows_de.first.inner_text() or ""
        ):
            log.info("The Data Explorer empty table message is displayed")
        n_de = rows_de.count()
        log.info("Number of rows in Data Explorer list found: %s", n_de)

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
        data_submission_create = DataSubmissionsListPage(hub).is_create_visible()
        header = HeaderPage(hub)
        header.open_user_menu()
        api_token = header.is_api_token_button_visible()
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
        ds_list = DataSubmissionsListPage(hub)
        if not ds_list.is_create_visible():
            return False
        ds_list.create_data_submission(
            "New/Update",
            "metadata only",
            "GC",
            AUTOMATION_STUDY_DS,
        )
        detail = DataSubmissionDetailPage(hub)
        detail.wait_loading_spinner_gone()
        return detail.is_cancel_visible()
    except Exception as exc:
        log.info("Error verifying permission - data_submission:cancel -> %s", exc)
        return False


def _functional_data_submission_review(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying DS Review...")
    try:
        _pbac_click_home(hub)
        _open_data_submissions_list_settled(hub)
        ds_list = DataSubmissionsListPage(hub)
        if not ds_list.is_create_visible():
            return False
        ds_list.create_data_submission(
            "New/Update",
            "metadata only",
            "GC",
            AUTOMATION_STUDY_DS,
        )
        detail = DataSubmissionDetailPage(hub)
        log.info("DS PBAC (review): waiting for detail loading spinner")
        detail.wait_loading_spinner_gone()
        temp = _prepare_unique_program_tsv()
        try:
            detail.upload_metadata_file(temp)
        finally:
            temp.unlink(missing_ok=True)
        log.info("DS PBAC (review): starting validation")
        detail.click_validate()
        log.info("DS PBAC (review): validation finished")
        detail.click_submit_for_review()
        detail.wait_loading_spinner_gone()
        return detail.is_release_reject_withdraw_visible()
    except Exception as exc:
        log.info("Error verifying permission - data_submission:review -> %s", exc)
        return False


def _functional_data_submission_admin_submit(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying DS Admin Submit...")
    try:
        _pbac_click_home(hub)
        _open_data_submissions_list_settled(hub)
        ds_list = DataSubmissionsListPage(hub)
        if not ds_list.is_create_visible():
            return False
        ds_list.create_data_submission(
            "New/Update",
            "metadata only",
            "GC",
            AUTOMATION_STUDY_DS,
        )
        detail = DataSubmissionDetailPage(hub)
        detail.wait_loading_spinner_gone()
        root = repo_root()
        invalid = root / PROGRAM_INVALID_TSV
        if not invalid.is_file():
            raise FileNotFoundError(invalid)
        detail.upload_metadata_file(invalid)
        detail.click_validate()
        return detail.is_admin_submit_enabled()
    except Exception as exc:
        log.info("Error verifying permission - data_submission:admin_submit -> %s", exc)
        return False


def _functional_data_submission_confirm(hub: Hub, user_role: str, scenario: str) -> bool:
    log.info("Verifying DS Confirm...")
    try:
        _pbac_click_home(hub)
        _open_data_submissions_list_settled(hub)
        ds_list = DataSubmissionsListPage(hub)
        if not ds_list.is_create_visible():
            return False
        ds_list.create_data_submission(
            "New/Update",
            "metadata only",
            "GC",
            AUTOMATION_STUDY_DS,
        )
        detail = DataSubmissionDetailPage(hub)
        log.info("DS PBAC (confirm): waiting for detail loading spinner")
        detail.wait_loading_spinner_gone()
        temp = _prepare_unique_program_tsv()
        try:
            detail.upload_metadata_file(temp)
        finally:
            temp.unlink(missing_ok=True)
        log.info("DS PBAC (confirm): starting validation")
        detail.click_validate()
        log.info("DS PBAC (confirm): validation finished")
        detail.click_submit_for_review()
        detail.wait_loading_spinner_gone()
        if user_role.lower() == "submitter" and scenario.lower() == "negative":
            return detail.is_cross_validate_or_release_or_complete_any_visible()
        detail.click_cross_validate()
        detail.click_release()
        detail.click_release_confirmation_yes()
        detail.wait_loading_spinner_gone()
        return detail.is_complete_and_reject_visible()
    except Exception as exc:
        log.info("Error verifying permission - data_submission:confirm -> %s", exc)
        return False


def _functional_program_manage(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Manage Programs...")
    try:
        _pbac_click_home(hub)
        header = HeaderPage(hub)
        header.open_user_menu()
        return header.is_nav_manage_programs_visible()
    except Exception as exc:
        log.info("Error verifying permission - program:manage -> %s", exc)
        return False


def _functional_study_manage(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Manage Studies...")
    try:
        _pbac_click_home(hub)
        header = HeaderPage(hub)
        header.open_user_menu()
        return header.is_nav_manage_studies_visible()
    except Exception as exc:
        log.info("Error verifying permission - study:manage -> %s", exc)
        return False


def _functional_institution_manage(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Manage Institutions...")
    try:
        _pbac_click_home(hub)
        header = HeaderPage(hub)
        header.open_user_menu()
        return header.is_nav_manage_institutions_visible()
    except Exception as exc:
        log.info("Error verifying permission - institution:manage -> %s", exc)
        return False


def _functional_user_manage(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Manage Users...")
    try:
        _pbac_click_home(hub)
        header = HeaderPage(hub)
        header.open_user_menu()
        return header.is_nav_manage_users_visible()
    except Exception as exc:
        log.info("Error verifying permission - user:manage -> %s", exc)
        return False


def _functional_dashboard_view(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Operation Dashboard...")
    try:
        _pbac_click_home(hub)
        header = HeaderPage(hub)
        header.open_user_menu()
        return header.is_nav_operation_dashboard_visible()
    except Exception as exc:
        log.info("Error verifying permission - dashboard:view -> %s", exc)
        return False


def _functional_access_request(hub: Hub, _role: str, _scenario: str) -> bool:
    log.info("Verifying Request Access...")
    try:
        _pbac_click_home(hub)
        HeaderPage(hub).open_profile()
        return UserProfilePage(hub).is_request_access_button_visible()
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
