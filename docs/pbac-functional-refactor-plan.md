# Plan: Refactor PBAC functional helpers into page objects

## Why this doc

`src/crdc_pw/utils/pbac_helpers.py` implements TC06+ **functional** permission checks by mirroring Katalon `Pbac.groovy` `permissionToCheck` closures. Many handlers mix **page object** calls with **inline** `hub.page.locator(hub.locators.get("CRDC/..."))` usage. That works but is hard to read and scatters DOM knowledge across utils and pages.

This document is a **plan only** (no code changes in this step). Implement in one or more follow-up PRs.

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
- **`_functional_*` handlers** repeat patterns that already exist partially on pages:
  - `HeaderPage`: nav / user menu (some PBAC code still uses raw locators for Data Explorer tab, API token, Profile link).
  - `DataSubmissionsListPage`: `create_data_submission` already opens the new submission; some handlers **click `DataSubmissionName-Link` again** (redundant with `_open_created_submission` — worth cleaning when refactoring).
  - `DataSubmissionDetailPage`: validate, upload patterns; PBAC duplicates `_upload_metadata_file_on_detail` inline instead of a page method.
  - `SubmissionRequestsListPage` / `SubmissionRequestFormPage`: mix of page API and raw locators for Review / Approve / Reject / Inquire / Submit.

**Docstring note:** `pbac_helpers` says *"DOM actions stay on … pages"* — the refactor brings the codebase in line with that intent.

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

- `click_home` or `go_home` — wrap `CRDC/NavBar/Home-Btn` (Katalon `SubmissionRequest.clickHome()`).
- `open_data_explorer` — today PBAC uses `Global/Header/Desktop/DataExplorer-Tab` after `open_user_menu()`; Katalon sometimes uses `CRDC/NavBar/DataExplorer-Tab`. Pick **one** canonical path used by the app in desktop layout; document if QA differs.
- `is_api_token_entry_visible` — user menu open + `APIToken-Btn` (for `data_submission:create`).
- `nav_bar_manage_*_visible` — optional thin wrappers if we want symmetry; PBAC currently checks `CRDC/NavBar/ManagePrograms-Btn` etc. Could be `is_manage_programs_visible_in_nav()` returning bool without navigating away.

### `DataSubmissionsListPage` (`data_submissions_list.py`)

- `is_create_data_submission_visible() -> bool` — replace repeated Create button locator blocks.
- `open_first_submission_from_list()` — only when list is already filtered to one row; **or** document that callers must use `create_data_submission` return and **not** double-click name link when already on detail.

### `DataSubmissionDetailPage` (`data_submission_details.py`)

- `upload_metadata_file(path: Path)` — encapsulate Choose Files → Upload → wait uploading hidden → wait Validate enabled (current `_upload_metadata_file_on_detail` in `pbac_helpers`).
- Optional composable steps for PBAC DS flows:
  - `submit_for_review()` — Submit + submit dialog confirm (paths in `AILocators/.../Actions` and `SubmitDialog`).
  - `cross_validate_then_release_confirm()` — for `data_submission:confirm` positive path.
  - `is_admin_submit_enabled_after_validate()` — admin_submit check.

Keep names aligned with Katalon keywords where it helps reviewers (`uploadMetadataUI`, `prepareUniqueMetadataAndUpload` logic can stay in utils or move to `utils/metadata_upload.py` — only if duplication grows).

### `SubmissionRequestsListPage` (`submission_requests_list.py`)

- Ensure list helpers cover: filter + **Resume** visibility, **Review** click, **Reopen** visibility (some exist already).
- Add typed methods that return **bool** for PBAC-style checks if that avoids importing locators into `pbac_helpers`.

### `SubmissionRequestFormPage` (`submission_request_form.py`)

- Review navigation: `open_review_section_with_approve_reject_inquire_visible()` wrapping Review progress + three buttons.
- Submit button visibility check could be `is_submit_button_visible()`.

### `ManageUsersPage` / `UserProfilePage`

- `is_request_access_button_visible()` when Profile is already open — PBAC opens Profile via header then checks `CRDC/ManageUsers/RequestAccess-Btn`.

---

## Implementation phases (suggested)

### Phase 1 — Low risk, high readability

- Add `HeaderPage.go_home()`, `HeaderPage.open_data_explorer()` (or nav variant), and DS list `is_create_visible()`.
- Replace corresponding lines in `pbac_helpers` only.
- Run: `pytest tests/unit -m unit -q`, `pytest tests/Pbac/test_TC06_CRDC-PbacCheckedPermissions-Fedlead.py -m CRDC_PBAC` on QA.

### Phase 2 — DS uploads and detail actions

- Move `_upload_metadata_file_on_detail` to `DataSubmissionDetailPage.upload_metadata_file`.
- Add submit / confirm / cross-validate / release helpers; refactor `_functional_data_submission_review|admin_submit|confirm|cancel`.
- **Remove redundant** `DataSubmissionName-Link` clicks where `create_data_submission` already landed on detail (verify with trace or stepping).

### Phase 3 — SR functional handlers

- Consolidate `_functional_submission_request_*` to use `SubmissionRequestsListPage` / `SubmissionRequestFormPage` only.
- Add small bool-returning helpers for "Review row visible", "form review actions visible".

### Phase 4 — Docs and cleanup

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
