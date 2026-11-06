# Plan: Refactor PBAC functional helpers into page objects

## Why this doc

`src/crdc_pw/utils/pbac_helpers.py` implements TC06+ **functional** permission checks by mirroring Katalon `Pbac.groovy` `permissionToCheck` closures. **Functional** handlers now delegate DOM to page objects; `pbac_helpers` keeps orchestration and Excel oracles.

This document tracks **planned** optional follow-ups and **what is done** in-repo.

---

## Completed (in codebase)

### Phase 1

- **`HeaderPage.go_home()`** — `CRDC/NavBar/Home-Btn` (Katalon `SubmissionRequest.clickHome`).
- **`HeaderPage.open_data_explorer()`** — user menu → Data Explorer (already present; used by `DataExplorerListPage`).
- **`DataSubmissionsListPage.is_create_visible()`** — PBAC gates for Create on the DS list.
- **`pbac_helpers`**: `_pbac_click_home` delegates to `go_home`; DS functional handlers use `is_create_visible` instead of inline Create locators.

### Phase 2

- **`DataSubmissionDetailPage.upload_metadata_file(path)`** — single-TSV upload with PBAC timeouts (120s uploading hidden, poll until Validate enables).
- **Submit / release / confirm**: `click_submit_for_review`, `click_release`, `click_release_confirmation_yes`, `click_cross_validate`, visibility helpers for cancel / review / admin submit / confirm branches.
- **`pbac_helpers`**: `_functional_data_submission_{cancel,review,admin_submit,confirm}` call the page APIs; removed `_upload_metadata_file_on_detail`, `_click_ds_submit_dialog_yes`, `_click_ds_release_confirmation_yes`, and redundant **`DataSubmissionName-Link`** clicks after `create_data_submission` (list flow already opens detail).

### Phase 3

- **`SubmissionRequestsListPage`**: `table_data_rows`, `is_start_submission_request_visible`, `is_resume_button_visible`, `save_unsaved_changes_dialog_if_present`, `return_to_list_after_partial_save`, `is_review_button_visible_on_list`, `click_review_on_first_matching_row`, `is_cancel_button_visible_on_first_row`, `is_reopen_button_visible`.
- **`SubmissionRequestFormPage`**: `is_submit_button_visible`, `are_review_decision_buttons_visible` (Approve / Reject / Inquire via existing nav paths + `_REJECT_BTN`).
- **`pbac_helpers`**: `_functional_submission_request_*` use the above only; removed `_sr_list_table_rows`, `_SR_REVIEW_BTN_LEGACY`, `_UNSAVED_SAVE`; row-scoped **Review** replaces global `Review-Btn`.

### Phase 4

- **`HeaderPage`**: `is_api_token_button_visible`, `is_nav_manage_{programs,studies,institutions,users}_visible`, `is_nav_operation_dashboard_visible` (user menu must be open; same AILocators Desktop paths as `open_manage_*`, not duplicate `CRDC/NavBar/*` keys).
- **`DataSubmissionsListPage` / `DataExplorerListPage`**: `table_data_rows()` for **`data_submission:view`**.
- **`UserProfilePage`**: `is_request_access_button_visible` (Profile open); **`access:request`** uses `HeaderPage.open_profile()` without duplicate Profile link clicks.
- **`pbac_helpers`**: module docstring clarifies orchestration-only; no `hub.page.locator(hub.locators.get(...))` in `_functional_*` handlers.

---

## Your questions — short answers

| Question | Answer |
|----------|--------|
| If we move those steps into page objects, would `pbac_helpers` look cleaner? | **Yes.** Helpers would mostly read as orchestration: navigate → call named screen methods → assert return value / visibility. |
| When something breaks, fix in page objects instead of `pbac_helpers`? | **Mostly yes** for broken **selectors** or **screen flows**. `pbac_helpers` would still own **which** flow proves **which** permission id, and **pytest.fail** / logging policy. |
| Can future tests reuse the new methods? | **Yes.** That is the main benefit: DS/SR/list/header flows become shared vocabulary. |

---

## Current state

- **Orchestration** (`verify_permissions_functional`, `edit_pbac_permissions`, Excel reads) stays in `pbac_helpers` — that is appropriate.
- **`_functional_*` handlers** call page objects only (Phases 1–4). Optional backlog: split handler bodies into `pages/pbac_functional.py` for file size only.
  - `HeaderPage`: PBAC chrome for API token, NavBar manage/dashboard entries (**Phase 4**).
  - `DataSubmissionsListPage` / `DataExplorerListPage` / `DataSubmissionDetailPage`: DS functional (**Phases 1–2, 4**).
  - `SubmissionRequestsListPage` / `SubmissionRequestFormPage`: SR functional (**Phase 3**).
  - `UserProfilePage`: Request Access on Profile (**Phase 4**).

**Docstring note:** `pbac_helpers` module doc states that functional checks delegate DOM to pages.

---

## Target state

1. **`pbac_handlers` module boundary (optional):** Keep `_PERMISSION_FUNCTIONAL` and handler **registration** in `pbac_helpers.py`, but each handler body should be **thin**: call page objects + return `bool`. Alternatively, move handler bodies to `pages/pbac_functional.py` — only if the team wants a shorter `pbac_helpers.py`; not required for the first pass.

2. **No raw `hub.page.locator(hub.locators.get(...))` in PBAC handlers** except where genuinely one-off (prefer zero).

3. **Use `BasePage._loc(path)`** inside page classes, not `page.locator(locators.get(...))` duplicated in utils.

4. **Single ownership** for common flows:
   - "Go home" / "wait DS loading gone" / "open Data Explorer from nav"
   - "Create DS with PBAC defaults (GC + ATS study)" if reused
   - "Upload a single TSV and wait for Validate enabled" (Katalon `uploadMetadataUI` parity)
   - "SR: filter In Progress + assert Cancel" etc.

---

## Candidate extractions (by file)

### `HeaderPage` (`header.py`)

- `go_home` — **done** — `CRDC/NavBar/Home-Btn` (Katalon `SubmissionRequest.clickHome()`).
- `open_data_explorer` — **done** — `Global/Header/Desktop/DataExplorer-Tab` after `open_user_menu()` (see `DataExplorerListPage`); Katalon sometimes uses `CRDC/NavBar/DataExplorer-Tab` — still **one** canonical path in code; document if QA differs.
- `is_api_token_button_visible` — **done** — user menu open + `APIToken-Btn`.
- User-menu visibility (PBAC manage / dashboard) — **done** — `is_nav_manage_*_visible`, `is_nav_operation_dashboard_visible` (`CRDC/AILocators/Global/Header/Desktop/Manage*-Link`, `OperationDashboard-Link`).

### `DataSubmissionsListPage` (`data_submissions_list.py`)

- `is_create_visible()` — **done** (same intent as “is Create visible”).
- `table_data_rows()` — **done** (PBAC `data_submission:view`).
- `create_data_submission` / `_open_created_submission` — opens detail; PBAC must not click `DataSubmissionName-Link` again (**done** in functional handlers).

### `DataSubmissionDetailPage` (`data_submission_details.py`)

- `upload_metadata_file(path)` — **done** (PBAC 120s semantics).
- PBAC flow steps — **done**: `click_submit_for_review`, `click_cross_validate`, `click_release`, `click_release_confirmation_yes`, plus visibility helpers (`is_cancel_visible`, `is_release_reject_withdraw_visible`, `is_admin_submit_enabled`, `is_complete_and_reject_visible`, negative-or helper for confirm).

Keep names aligned with Katalon keywords where it helps reviewers (`uploadMetadataUI`, `prepareUniqueMetadataAndUpload` logic can stay in utils or move to `utils/metadata_upload.py` — only if duplication grows).

### `DataExplorerListPage` (`data_explorer_list.py`)

- `table_data_rows()` — **done** (PBAC `data_submission:view`).

### `SubmissionRequestsListPage` (`submission_requests_list.py`)

- **Done (PBAC)**: `table_data_rows`, `is_start_submission_request_visible`, `is_resume_button_visible`, unsaved-dialog save + `return_to_list_after_partial_save`, Review visibility + `click_review_on_first_matching_row`, Cancel, Reopen helpers. Filters / `open` / row actions unchanged for CRDCDH-3948 etc.

### `SubmissionRequestFormPage` (`submission_request_form.py`)

- **Done (PBAC)**: `is_submit_button_visible`, `are_review_decision_buttons_visible` (with `click_review_progress_bar` still used by handlers).

### `ManageUsersPage` / `UserProfilePage`

- `UserProfilePage.is_request_access_button_visible()` — **done** — Profile open; `CRDC/ManageUsers/RequestAccess-Btn`.

---

## Implementation phases (suggested)

### Phase 1 — Low risk, high readability (done)

- Add `HeaderPage.go_home()`, `HeaderPage.open_data_explorer()` (or nav variant), and DS list `is_create_visible()`.
- Replace corresponding lines in `pbac_helpers` only.
- Run: `pytest tests/unit -m unit -q`, `pytest tests/Pbac/test_TC06_CRDC-PbacCheckedPermissions-Fedlead.py -m CRDC_PBAC` on QA.

### Phase 2 — DS uploads and detail actions (done)

- Move `_upload_metadata_file_on_detail` to `DataSubmissionDetailPage.upload_metadata_file`.
- Add submit / confirm / cross-validate / release helpers; refactor `_functional_data_submission_review|admin_submit|confirm|cancel`.
- **Remove redundant** `DataSubmissionName-Link` clicks where `create_data_submission` already landed on detail (verify with trace or stepping).

### Phase 3 — SR functional handlers (done)

- Consolidate `_functional_submission_request_*` to use `SubmissionRequestsListPage` / `SubmissionRequestFormPage` only.
- Add small bool-returning helpers for "Review row visible", "form review actions visible".

### Phase 4 — Docs and cleanup (done)

- Update `docs/onboarding.md` PBAC section if public API names change.
- Short comment at top of `pbac_helpers`: handlers must delegate DOM to pages.

---

## Testing and regression

- **Unit:** No change expected unless new pure helpers get tests.
- **Integration:** TC06 full run; spot-check one SR test (`CRDCDH-3948`) and one DS test (`CRDCDH-697`) if Phase 2 touches shared page code.
- **Rule:** Prefer **one** behavioral change per PR (extract + call-site replace) to bisect failures.

---

## Risks and notes

1. **Locator path drift:** `CRDC/NavBar/...` vs `CRDC/AILocators/Global/Header/Desktop/...` — align with what production QA uses; add a one-line comment in `HeaderPage` when standardizing.

2. **Redundant navigation:** Double-clicking submission name after `create_data_submission` may be unnecessary or could mask list state bugs; removing it is a **small behavior change** — verify once on QA.

3. **Negative scenario (TC11+):** When implemented, same page APIs should support `expect False` branches; keep handler signatures `(hub, role, scenario)`.

4. **File size:** `pbac_helpers.py` is large; optional split of handler bodies is a **style** decision, not required for cleanliness if pages absorb DOM.

---

## Success criteria

- PBAC functional handlers are **mostly** 5–15 line functions that call page APIs.
- Selector / wait fixes happen **primarily** under `src/crdc_pw/pages/`.
- New Hub tests can reuse the same methods without copying `hub.locators.get(...)`.

---

## Out of scope (for this refactor)

- Changing PBAC **oracle** behavior (`pbac_sheet`, Excel columns, skip messages).
- TC11 negative functional port (unless a shared uncheck API is needed on `ManageUsersPage` — already planned separately).
