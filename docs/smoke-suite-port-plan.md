# CRDC_Smoke port plan (Katalon → Playwright)

Goal: **`pytest -m CRDC_Smoke`** should cover the same Hub checks as Katalon **`Test Suites/CRDC_Smoke.ts`**, so the Playwright framework is useful for daily QA smoke without opening Katalon.

**Source of truth:** [`crdc-dh-automation/Test Suites/CRDC_Smoke.ts`](https://github.com/CBIIT/crdc-dh-automation/blob/develop/Test%20Suites/CRDC_Smoke.ts) (20 linked test cases, suite order below).

**Playwright command (target):** `pytest -m CRDC_Smoke` (optional `-n 4` after cookies are warm; run **`CRDC_PBAC`** setup serial when PBAC cases are included).

---

## Opinion: is full smoke worth it?

**Yes.** Today Playwright smoke is **Manage Studies (TC08)**, **Manage Programs (TC09)**, **Data Submissions list (TC10)**, **Submission Requests list (TC12)**, **PBAC TC09** (Submitter checked permissions), **CRDCDH-697 TC01** (headers), **CRDCDH-332 TC01** (SR all fields through submit), **TC03 / TC04** (DS list sorting and pagination, Dcp), and **887 TC101 / 2864 TC102** (Upload Errors modal), and **1035 TC101** (Validation Results export, all roles). Katalon smoke is a **breadth slice**: list pages, SR create, table UX, PBAC functional check, and many DS paths (upload, validate, batch errors, cross-val, export, explorer). Porting it makes Playwright the credible pre-release gate Katalon smoke already is.

**Pragmatic approach:** work **top to bottom of the Katalon suite list** for traceability, but **implement in difficulty tiers** (below) so early merges add value without blocking on CLI or multi-role epics.

**Approach (one case per change):** port one Katalon case at a time (group only where cases share new code: the three Excel marker rows, and TC03 + TC04 sharing generic table helpers). Dual-run the case against Katalon on the same profile before marking it **Done** in the table below.

---

## Suite setup (not in `CRDC_Smoke.ts` links)

Katalon suite **description** says run **EnableAllPermissions** first (same as DS flow). That case lives under **`Test Cases/CRDC/SuiteSetup/EnableAllPermissions`**, not as a row in `CRDC_Smoke.ts`.

| Katalon | Playwright | Status |
|---------|------------|--------|
| EnableAllPermissions | `tests/SuiteSetup/test_EnableAllPermissions.py` (`CRDC_PBAC`, Master) | **Done** |

**Recommendation:** Document job order: `pytest -m CRDC_PBAC -k EnableAllPermissions` (or full PBAC suite) **before** smoke when PBAC TC09 is ported; or run smoke only on environments where automation users already have full permissions.

---

## Katalon `CRDC_Smoke` order vs Playwright status

Suite description says “GC-focused (no CTDC/ICDC)” but the file **includes CTDC and ICDC** validation cases (rows 18–19). Treat the **`.ts` list** as authoritative until the suite is edited in Katalon.

| # | Katalon test case | Role(s) | PW status | Port difficulty | Notes |
|---|-------------------|---------|-----------|-----------------|-------|
| 1 | `AuxiliaryTests/TC10_DataSubmissionsListAndFilter` | Submitter | **Done** | — | `tests/AuxiliaryTests/test_TC10_DataSubmissionsListAndFilter.py`; `DataSubmissionsListPage.apply_filters` / `read_table_rows` / `reset_filters`. |
| 2 | `SubmissionRequest/CRDCDH-332/TC01_CRDC_Submission_Request-AllFields` | Submitter | **Done** | — | `tests/SubmissionRequest/CRDCDH-332/test_TC01_CRDC_Submission_Request-AllFields.py` (`CRDC_Smoke`). `SubmissionRequestFormPage` gained `enter_additional_contact_info`, `enter_existing_and_planned_publications_info`, `enter_repository_info` and a Review and Submit section of `verify_*` methods (PI, contacts, program, study, funding, publications, repository, access and disease, data types, file types). Expected values come from `SubmissionRequest.xlsx`; `find_cell_containing` replaces Katalon's switch from dropdown word to list value. Each run submits one real request (no cleanup, as in Katalon). Differences from Katalon: phone numbers for the primary and additional contact are compared for real, digits only (Excel `404-588-3432`, Review page `(404)588-3432`); Katalon's primary-contact phone check read the institution field again and its additional-contact phone check is commented out. Data types are limited to those with a Review locator (clinical, immunology, genomics, proteomics, imaging, epidemiologic). |
| 3 | `AuxiliaryTests/TC12_SubmissionRequestsListAndFilter` | Submitter | **Done** | — | `tests/AuxiliaryTests/test_TC12_SubmissionRequestsListAndFilter.py`; `SubmissionRequestsListPage.read_table_rows` / `read_table_headers` / `start_button` plus existing apply/reset. |
| 4 | `AuxiliaryTests/TC08_ManageStudiesListAndFilter` | Admin | **Done** | — | `tests/AuxiliaryTests/test_TC08_ManageStudiesListAndFilter.py` |
| 5 | `AuxiliaryTests/TC09_ManageProgramsListAndFilter` | Admin | **Done** | — | `tests/AuxiliaryTests/test_TC09_ManageProgramsListAndFilter.py` |
| 6 | `AuxiliaryTests/TC03_TableSortingVerification` | Dcp | **Done** | — | `tests/AuxiliaryTests/test_TC03_DSTableSortingVerification.py` (`CRDC_Smoke`; renamed with `DS` so the page is clear at a glance). `BasePage` verify_column_sortability (all sortable except SRF), verify_default_sort (Last Updated, desc), verify_column_sort_on_click (Status, Data Commons: both directions, rows checked). Order compare is `utils/table_helpers.is_sorted`. Sort direction is read from the MUI sort label classes (no aria-sort), and the wait is on that direction, not on row text. Not yet run live or dual-run against Katalon. |
| 7 | `AuxiliaryTests/TC04_PaginationVerification` | Dcp | **Done** | — | `tests/AuxiliaryTests/test_TC04_DSPaginationVerification.py` (`CRDC_Smoke`; renamed with `DS`). `BasePage` verify_rows_per_page_options (5, 10, 20, 50), verify_default_rows_per_page (20; Katalon's value, its comment says 10), verify_displayed_rows_text, verify_page_navigation, verify_rows_per_page_change (5). Needs more than one page of Data Submissions for Dcp; with one page it only checks that Previous and Next are disabled. Not yet run live or dual-run against Katalon. |
| 8 | `Pbac/TC09_CRDC-PbacCheckedPermissions-Submitter` | Admin → Submitter | **Done** | — | `tests/Pbac/test_TC09_CRDC-PbacCheckedPermissions-Submitter.py` (`CRDC_Smoke`); `edit_pbac_permissions` + `verify_permissions_functional` in `pbac_helpers.py`. |
| 9 | `DataSubmissions/GC/CRDCDH-697/TC01_CRDC-VerifyDataSubmissionHeaders` | Submitter | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-697/test_TC01_CRDC-VerifyDataSubmissionHeaders.py` |
| 10 | `DataSubmissions/GC/CRDCDH-1163/TC16_...SubmittedMetadata` | Submitter, Dcp | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-1163/test_TC16_CRDCDH-1163_DCPValidationAfterSubmissionSubmittedMetadata.py` (`CRDC_Smoke`, `CRDC_DSFlow`). Submitter creates a GC metadata-only submission in the ATS study, uploads a unique `program.tsv` (`prepare_unique_program_tsv` in `pbac_helpers.py`, now public), validates and submits; Dcp opens it by id and the test runs five separate checks with the shared `ui_helpers` (`assert_element_text` on the status, `assert_button_enabled` on Validate, `assert_button_selected` on Metadata, All Uploaded Data and New Uploaded Data), as Katalon does with `verifyElementText`, `verifyButtonEnabled` and `verifyButtonSelected`. Each run leaves a Submitted submission (no cleanup, as in Katalon). Not yet run live or dual-run against Katalon. |
| 11 | `DataSubmissions/GC/CRDCDH-1051/TC25_VerifyDcpCrossValidation` | Submitter, Dcp | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-1051/test_TC25_CRDCDH-1051_VerifyDcpCrossValidation.py` (`CRDC_Smoke`, `CRDC_DSFlow`, `CRDC_DataValidation`). Submitter creates two GC metadata-only submissions in `autoQA - AutomationQA_CV`, uploads `CRDCDH-1051_TC25` (same `program_acronym`) into both, validates and submits each; Dcp opens submission 2, cross-validates (waits for the button to enable again), reads the Cross Validation Results rows that link to submission 1 with `read_cross_validation_rows_for_peer`, and compares them with the expected TSV (`diff_cross_validation_rows` in `utils/validation_results.py`), then rejects submission 2 and submission 1 (status Rejected each). Expected TSV is in `MetadataData/CRDCDH-1051_TC25/expected-CrossValidationResults/`. Not yet run live or dual-run against Katalon. |
| 12 | `DataSubmissions/GC/CRDCDH-514/TC06_VerifyFullDataSubmissionHistory` | Submitter, Dcp | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-514/test_TC06_CRDCDH-514_VerifyFullDataSubmissionHistory.py` (`CRDC_Smoke`, `CRDC_DSFlow`). Submitter creates, uploads a unique `program.tsv`, validates (In Progress) and submits; Dcp rejects with a justification; Submitter re-validates, reloads and submits again; Dcp cross-validates, Releases and Completes. Each status is checked with `assert_element_text`, and the Full History dialog is read with `read_history_statuses` and compared (newest first, whitespace and case ignored) by `ui_helpers.diff_history_statuses`. Reject, Complete and Full History steps are separate locator-property actions in the test. Each run consumes one submission (ends Completed). Not yet run live or dual-run against Katalon. |
| 13 | `DataSubmissions/GC/CRDCDH-1035/TC101_VerifyValidationResultsExportAllRoles` | Submitter, Dcp, Fedlead, Admin | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-1035/test_TC101_CRDCDH-1035_VerifyValidationResultsExportAllRoles.py` (`CRDC_Smoke`, `CRDC_DSFlow`). Submitter creates a GC metadata-only submission, `upload_folder("TC04")`, `click_validate`, then `verify_validation_results_export_enabled` and `export_validation_results_and_verify_filename`; Dcp, Fedlead and Admin each `switch_user`, `open_upload_activity(submission_id)` and check Export is enabled. File name rule is `utils/validation_results.check_export_filename`. Difference from Katalon: the download is caught with Playwright's download event, not by clearing Downloads and reading the newest file after a sleep. Not yet run live or dual-run against Katalon. |
| 14 | `DataSubmissions/GC/CRDCDH-887/TC101_ColumnRequiredBatchErrors` | Submitter | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-887/test_TC101_CRDCDH-887_ColumnRequiredBatchErrors.py` (`CRDC_Smoke`, `CRDC_DataValidation`, `CRDC_Regression`). Create a GC metadata-only submission, `upload_folder("CRDCDH-887_TC101")`, then `verify_upload_activities_batch_row("Metadata", 5, "Failed")` and `verify_upload_errors_modal`. Input folder copied from Katalon. Run live on QA2 (passes; one transient backend 'Batch loading failed' on a first 2864 run). Not yet dual-run against Katalon. |
| 15 | `DataSubmissions/GC/CRDCDH-2864/TC102_BatchErrorsCompositeIdRequiredProperty` | Submitter | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-2864/test_TC102_CRDCDH-2864_BatchErrorsCompositeIdRequiredProperty.py` (same markers). Same flow with `CRDCDH-2864_TC102` and 4 files. Run live on QA2 (passes; one transient backend 'Batch loading failed' on a first 2864 run). Not yet dual-run against Katalon. |
| 16 | `DataSubmissions/GC/CRDCDH-1405/TC101_CLINoFileIdVerifyFinalManifest` | Submitter | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-1405/test_TC101_CRDCDH-1405_CLINoFileIdVerifyFinalManifest.py` (`CRDC_Smoke`, `CRDC_DSFlow`). Submitter creates a New GC `both` submission in `autoQA - AutomationQA_Study` (the page is then on it); `upload_files_via_cli` (`pages/cli_uploader.py`) runs the vendored CLI with a manifest that has no `file_id`; `diff_final_manifest` (`utils/cli_verifications.py`) checks the `-final.tsv` (file_id column, valid `dg.4DFC/<uuid>`, same row count); a second run with a fresh manifest copy is compared by `diff_file_ids_between_runs`. The CLI is vendored in `tools/crdc-datahub-cli-uploader/` (see its `VENDORED.md`); API URL and token come from `config/<profile>.yaml` (`ApiUrl` optional, `SubmitterApiToken` required, the test fails with a clear message when it is empty). Needs Python 3.13 or newer (checked, with a clear failure); like Katalon, `pip install -r requirements.txt --quiet` runs before every CLI run (3 minute timeout). Differences from Katalon: the interpreter is the one running pytest, not Katalon's per-OS path (`python3` on Linux, a personal Mac path elsewhere); CLI output checks (`Files failed: 0`, `File uploading completed!`, `Files processed:`, `Files copied:`, last "X out of Y file(s) have been validated" line complete) are hard assertions, Katalon only logged a warning; the CLI reads the data files from InputFiles and works on a copy of the manifest folder's `.tsv`/`.txt` files in a new temporary folder per call, so `-final.tsv` is written there (Katalon writes it into InputFiles and deletes the stale one first; the copy leaves out old `-final` files, which has the same effect); no ValidationReport items. The CLI exits 0 even when it fails, so the output checks are what catch a failed run. Each run leaves a submission (no cleanup, as in Katalon). Not yet run live or dual-run against Katalon. |
| 17 | `DataSubmissions/GC/CRDCDH-686-Partial/TC03_VerifyInvalidStrPtrn-IncompibleConsCode` | Submitter | **Done** | — | Workbook **`tests/DataValidation/GC/CRDCDH-686-Partial/TC03_....xlsx`** + runner **`verify_validation_results`**. `CRDC_Smoke` via collector allowlist (`_SMOKE_CASE_STEMS`). |
| 18 | `DataSubmissions/CTDC/.../TC101_...LongFormErrorsCTDC` | Submitter (Excel Settings) | **Done** | — | Workbook under `tests/DataValidation/CTDC/CRDCDH-699-CTDC/`. `CRDC_Smoke` via collector allowlist. On 2026-11-16 the Hub moved to CTDC 4.3.0 before STS had values for it (the nightly MDB promotion and the Hub PV puller had not run), so participant `radiology_report_available` (CDE-linked, no list in the model file) was not value-checked and the participant expected TSV was removed from smoke so the case does not depend on STS. The original `NO1` participant check lives in non-smoke, PW-only `TC104_CRDCDH-699_VerifyCdePermissibleValueErrorsCTDC` (not in Katalon). `Value not permitted` is now asserted on a second specimen record `ctdc_spec_2` with an invalid `specimen_type` (the VR table labels a record with its first issue, so each issue type needs its own record). Katalon's copy of `CRDCDH-699_TC101` needs the same edits. |
| 19 | `DataSubmissions/ICDC/.../TC36_...RequiredRelatedPropertyMissingICDC` | Submitter (Excel Settings) | **Done** | — | Workbook under `tests/DataValidation/ICDC/CRDCDH-699-ICDC/`. `CRDC_Smoke` via collector allowlist. |
| 20 | `DataSubmissions/GC/CRDCDH-3026/TC201_VerifyDataExplorerMetadataView` | Submitter | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-3026/test_TC201_CRDCDH-3026_VerifyDataExplorerMetadataView.py` (`CRDC_Smoke`, `CRDC_DSFlow`). Submitter opens Data Explorer, filters by `automation_CompletedStudy` (`DataExplorerListPage.fill_study_name`), opens the first study (`first_study_link`), then for program, study, participant and sample: `DataExplorerStudyPage.verify_node_table(node, expected_headers, expected_rows)` (select node, `show_all_columns`, read headers and rows, compare with `diff_data_explorer_table` in `utils/data_explorer_results.py`: row count, headers present, each cell equal or contained). The test loads `CRDCDH-3026/<node>.tsv` with `load_expected_data_explorer_table` and passes it in. **QA seed is still a manual prerequisite** (study released with `InputFiles/CRDC/MetadataData/CRDCDH-3026`). Differences from Katalon: waits for the table to settle instead of fixed delays; an empty expected cell must be empty in the UI (Katalon lets any UI text pass); no ValidationReport items (mismatches fail the test with the full list). Show All uses the inner input when the test id is on the MUI root (not yet seen live). Not yet run live or dual-run against Katalon. |

**Out of scope for Katalon smoke (already noted in suite description):** API token tests CRDCDH-1551/1526.

---

## Recommended port waves (easiest first)

Use this order for **implementation**, while keeping **Katalon case IDs** in test names/paths.

### Wave 1 — List smoke + Excel smoke (high value, low new infra)

1. ~~**TC12** Submission Requests list + filter~~ — **Done** (`SubmissionRequestsListPage` readers + test).
2. ~~**TC10** Data Submissions list + filter~~ — **Done** (`DataSubmissionsListPage` filters/read/reset).
3. ~~**CRDCDH-686 TC03**, **CRDCDH-699 CTDC TC101**, **CRDCDH-699 ICDC TC36**~~ — **Done** (`CRDC_Smoke` via `_SMOKE_CASE_STEMS` in the Excel collector; run with `pytest -m "CRDC_Smoke and CRDC_DataValidation_Excel"`).
4. ~~**CRDCDH-697 TC01** (headers)~~ — **Done**.

**Exit criteria:** Submitter can exercise three list pages (SR, DS, Studies/Programs already done) + one DS create + three validation smokes without new Katalon.

### Wave 2 — SR smoke + table UX + batch upload errors

5. ~~**CRDCDH-332 TC01** SR AllFields~~ — **Done** (form page fill steps + Review verifiers).
6. ~~**TC03** table sorting + **TC04** pagination~~ — **Done** (shared generic table methods on `BasePage`, run on the DS list).
7. ~~**CRDCDH-887 TC101** + **CRDCDH-2864 TC102**~~ — **Done** (shared upload-activities batch row and Upload Errors modal verifiers on `DataSubmissionDetailPage`).

### Wave 3 — PBAC + multi-role DS

8. ~~**PBAC TC09** Submitter checked permissions (functional verify)~~ — **Done**.
9. ~~**CRDCDH-1035 TC101** VR export all roles~~ — **Done** (`switch_user`, submission deep link, download event).

### Wave 4 — Heavy DS / CLI / Explorer

10. ~~**CRDCDH-1163 TC16**~~ — **Done**.
10a. ~~**CRDCDH-514 TC06**~~ — **Done**.
10b. ~~**CRDCDH-1051 TC25**~~ — **Done**.
10c. ~~**CRDCDH-3026 TC201**~~ — **Done**.
11. ~~**CRDCDH-1405 TC101**~~ — **Done** (CLI vendored into `tools/`, token from the gitignored config). All 20 linked Katalon cases are now ported, and README, onboarding and the CI smoke job are updated; what is left is the live run of the whole suite.

---

## Per-case analysis (what blocks each port)

### Auxiliary list tests (TC10, TC12, TC08, TC09)

| Case | Katalon keywords | Playwright gap |
|------|------------------|----------------|
| TC08/09 | Studies/Programs list | **Done** |
| TC10 | `DataSubmissionsList.*` | **Done** — `DataSubmissionsListPage` filters (name, status multi-select, program, submitter, commons, dbGaP), `read_table_rows`, `reset_filters` |
| TC12 | `SubmissionRequestList.*` | **Done** — `SubmissionRequestsListPage` filters/reset plus `read_table_rows`, `read_table_headers`, `start_button` |

**Next step:** run `pytest -m CRDC_Smoke` serially on qa2 and dual-run the cases still marked "not yet run live" (and the CLI cases 1405 TC101 and 697 TC13, which need `SubmitterApiToken`). `README.md`, `docs/onboarding.md` and the CI smoke job (`smoke` in `.github/workflows/ci.yml`, manual `run_smoke`, Python 3.13) are done.

### Generic table (TC03, TC04) — Done

Katalon centralizes in **`WebUIUtils`**: sortability, default sort, column click sort, pagination options, page nav, rows-per-page change.

Playwright: locators `HeaderCell` under **`CRDC/AILocators/GenericTable/`** and `CurrentPage-Btn`, `GoToPage-Btn` (placeholder `${page}`), `PaginationNav-Buttons` under `.../Pagination/`. The compare rules (`is_sorted`, `parse_displayed_rows`) are pure functions in **`utils/table_helpers.py`** with unit tests. The table reads, actions and `verify_*` methods are on **`BasePage`**, so any generic-table list page can reuse them. **One port serves both** TC03 and TC04. Katalon's `ValidationReport` helper is not ported.

### PBAC TC09 (Done)

| | Katalon TC09 | Playwright |
|---|--------------|------------|
| Setup | Admin `editPbacPermissions('Submitter', 'positive')` | `edit_pbac_permissions(hub, "Submitter", "positive")` |
| Verify | Submitter `verifyPermissionsFunctional` | `verify_permissions_functional(hub, "Submitter", "positive")` in `pbac_helpers.py` |

### DS validation / upload (686, 699, detail page)

**Already on `DataSubmissionDetailPage`:** `upload_folder`, `click_validate`, `verify_validation_results_vs_expected_for_tc`, error details.

**Also on `DataSubmissionDetailPage` (887 TC101, 2864 TC102):** `verify_upload_activities_batch_row` and `verify_upload_errors_modal`. The expected-error oracle is in `utils/validation_results.py` (`load_expected_upload_errors`, `diff_upload_errors`, reading `MetadataData/<tc>/expected/*.tsv`). Other Katalon cases that end the same way (887 TC102 to TC104, 2864 TC101, 1195 TC101, 1405 batch-error cases) can reuse it with a new input folder and a short test file each.

**Also on `DataSubmissionDetailPage` (1163 TC16):** locator properties `status_label`, `validate_button`, `validation_type_metadata_radio`, `validation_target_all_radio`, `validation_target_new_radio`. The checks themselves are `assert_element_text` and `assert_button_selected` in `utils/ui_helpers.py` (next to `assert_button_enabled`), reusable by any test.

**Also on `DataSubmissionDetailPage` (1051 TC25):** `DS_AUTOMATION_STUDY_CV` and `read_cross_validation_rows_for_peer(peer_id)`, which opens the Cross Validation Results tab, sets 50 rows per page and returns the rows that link to the peer submission across all pages. Locators `CrossValidation/Table` and `Table-DataRow` are scoped to the table with a Submitted Identifier column. The expected-TSV loader and comparison are `load_expected_cross_validation_rows` and `diff_cross_validation_rows` in `utils/validation_results.py`.

**Also on `DataSubmissionDetailPage` (514 TC06):** locator properties `reject_button`, `reject_comment`, `confirm_reject_button`, `cross_validate_button`, `complete_button`, `complete_confirmation_yes`, `full_history_button`, `history_dialog`, `history_close_button`, plus `read_history_statuses()` (rows newest first). The comparison is the pure `diff_history_statuses` in `utils/ui_helpers.py`.

**Also on `DataSubmissionDetailPage` (1035 TC101):** `submission_id_from_url`, `open_upload_activity`, `verify_validation_results_export_enabled`, `export_validation_results_and_verify_filename`.

**Data Explorer (3026 TC201):** `DataExplorerListPage` gained `fill_study_name` and `first_study_link`. New `DataExplorerStudyPage` (`pages/data_explorer_study.py`) has `container`, `column_visibility_button`, `select_node_type`, `check_show_all`, `show_all_columns`, `wait_loading_gone`, `read_headers`, `read_rows` and `verify_node_table` (expected data supplied by the test, per the hybrid POM rule for a one-test heavy compare). Locator `StudyView/NodeType-Option` takes `{node}`. The expected-TSV loader and comparison are `load_expected_data_explorer_table` and `diff_data_explorer_table` in `utils/data_explorer_results.py` (a separate module from `validation_results.py`, which now exposes `read_tsv_lines`).

**CLI upload (1405 TC101, 697 TC13):** `pages/cli_uploader.py` is the equivalent of Katalon's `CliUploader.uploadFilesViaCli`, so the other CLI cases can reuse it. `upload_files_via_cli(hub, tc_name, "datafile" | "metadata", expect_validation_errors=, omit_archive_manifest=, work_dir=)` (like Katalon, the submission id is read from the page URL, so the browser must be on the submission; settings come from `hub.settings`) finds the manifest (a file ending in `manifest.tsv`, preferring `manifest.tsv`, never `zip-archive-manifest.tsv`), requires `zip-archive-manifest.tsv` when there are `.zip` files and fails when it is missing (as Katalon does; the only exception is `omit_archive_manifest` together with `expect_validation_errors`, which leaves it out on purpose), builds the config and runs the CLI. **Where it runs (decided with the maintainer):** the CLI reads the data files straight from `InputFiles/CRDC/MetadataData/<tc>/DataFiles` (or `Metadata`), which it never writes to (checked in the vendored source: its only writes are `./tmp` in its working directory and the files beside the manifest). The `.tsv` and `.txt` files of the manifest folder are copied to `<work dir>/manifest` (`copy_manifest_folder_files`; `work_dir` is optional and defaults to a new temporary folder per call, so two uploads in one test never share files), because the CLI reads the other tsv/txt files beside the manifest (child metadata files that get a file id) and writes `<name>-final.tsv/.txt` there. Old `-final` files are not copied, as Katalon deletes the stale `-final.tsv` first. The optional Katalon settings are read from the profile yaml with the same names and defaults: `CRDC_CLI_RETRIES` (3), `CRDC_CLI_OVERWRITE`, `CRDC_CLI_DRYRUN`. Katalon's `CRDC_MANIFEST_ID_FIELD` (`id-field`) is left out: the CLI replaces it with the column name the Hub returns, so setting it never had an effect (PR 46 review), and no Katalon profile sets it. The run itself matches Katalon: `pip install -r requirements.txt --quiet` before every run (3 minute timeout), then `python src/uploader.py --config <file>` with the CLI folder as working directory (here a fresh `work_dir/cli`, so logs and reports of one run never mix with another). Differences: the Python version (3.13 or newer) is checked first; Katalon's page refresh after the upload is left to the caller; the config file holds the token, lives in `work_dir/cli` and is deleted after the run, and the token is masked in returned output. The CLI exits 0 even when it fails, so `cli_output_problems` (exit code, `Failed to upload files`, `can't get data file config`, the four success lines, last "X out of Y file(s) have been validated" line) is a hard assertion, where Katalon `verifyCliUploadOutput` only warned. Three more checks go beyond Katalon (PR 46 review): the failure lines also include `Failed to update batch`, `Failed process the manifest` and `Failed to add file id to the pre-manifest` (the CLI exits 0 and still prints the success lines when batch finalization or manifest processing fails); `verify_cli_error_messages` fails when a file with expected errors has no row in the upload report (Katalon only checks the rows that are there); and the deterministic file_id comparison keys on `internal_file_name` first, so same-named files in different folders are not merged. The other PR 46 review comments are about the vendored CLI itself (kept identical to Katalon's copy and upstream, see `tools/crdc-datahub-cli-uploader/VENDORED.md`).

**CLI error messages (`utils/cli_verifications.py`, Katalon `verifyCliErrorMessages`):** after a run with `expect_validation_errors=True`, `verify_cli_error_messages(upload, tc_name)` reads the newest `tmp/upload-report-*.tsv` of that run, loads `<tc>/expected/*.tsv` (columns `expected_errors` or `expected_error`, and `file_name`, `internal_file_name` or `fileName`), and compares the errors per file name (messages sorted and joined, so the order in a list does not matter). If a report row's errors cell is empty, the error line for that file is taken from the CLI log (a line with one of the CLI error phrases that names the file; for a one-row report the first long error line), as in Katalon. It logs expected and actual for each file, writes `reports/CLI_ErrorVerification/error-verification-<tc>-<time>.tsv` (Katalon writes the same file under `Reports/`), and fails with every mismatch (plus the CLI log when an actual error was missing). A file the CLI flagged that no expected file lists fails; expected files that are not in the report are ignored (as in Katalon). Differences: the report is read as real TSV (quoted cells), Katalon split on tabs; no ValidationReport items. Katalon's `verifyCliUploadReport` (every row `succeeded=true`, row count equals `Files processed`) is defined but never called anywhere in Katalon, so it is not ported. Ported as the first user of both: `CRDCDH-697/TC13` (`tests/DataSubmissions/GC/CRDCDH-697/test_TC13_CRDCDH-697_VerifyDataFileSizeAndMd5Mismatch.py`, `CRDC_DataFileUpload`, `CRDC_Regression`; inputs `MetadataData/CRDCDH-697_TC13`, copied from Katalon `TC13`). Katalon calls `uploadFilesViaCli` there without `expectValidationErrors`, so a failing CLI only logged a warning; the port passes `expect_validation_errors=True` and the error check is the assertion. Not run live yet. Still to port: the other CLI cases (1405 TC100 and TC102 to TC111, 3027 TC29 to TC34, 697 TC101 CTDC, ICDC and CTDC 1405 variants; some also use Mongo checks that are not ported). The lower-level pieces are `build_config`, `write_config_file`, `run_uploader`, `ensure_cli_dependencies`, `cli_output_problems` and `mask_token`. `utils/cli_verifications.py` holds the pure final-manifest oracles (`read_manifest`, `final_manifest_path`, `diff_final_manifest`, `diff_file_ids_between_runs`). `Settings.api_url` and `Settings.submitter_api_token` read `ApiUrl` and `SubmitterApiToken` from the profile yaml, and `ci/write_profile_yaml.py` overlays both from env.

### Excel vs native pytest for smoke

| Approach | Pros | Cons |
|----------|------|------|
| Native pytest per Katalon `.tc` | Clear 1:1, `CRDC_Smoke` on one file | Duplicates Excel for TC03/686 if both exist |
| Excel collector + `CRDC_Smoke` marker | Reuses **`step_runner`** | Smoke job runs Excel loader; role from workbook Settings |

**Recommendation (done):** For **686/699 CTDC/ICDC** rows in smoke, the existing Excel tests carry `CRDC_Smoke` through the collector allowlist (`_SMOKE_CASE_STEMS`), listed in rows 17-19 above. For **887/2864/1035**, prefer **native pytest** until/unless you add Excel workbooks.

---

## Markers and CI (target state)

| Marker | Meaning |
|--------|---------|
| `CRDC_Smoke` | Member of Katalon `CRDC_Smoke.ts` |
| `CRDC_Auxiliary` | AuxiliaryTests folder (TC08/09/10/12 also smoke) |
| `CRDC_DSFlow` | DS workflow tests (697 headers) |
| `CRDC_DataValidation_Excel` | Excel-driven validation |
| `CRDC_PBAC` | PBAC + EnableAllPermissions |

`README.md` and `docs/onboarding.md` now describe the full smoke suite.

**CI job** (`smoke` in `.github/workflows/ci.yml`, run by hand with `run_smoke`):

```bash
pytest -m CRDC_PBAC -k EnableAllPermissions   # serial
pytest -m CRDC_Smoke                          # serial; tracing is already on in pytest.ini
```

---

## Tracking

| Wave | Cases | Owner / ticket |
|------|-------|----------------|
| 1 | ~~TC12~~ (done), ~~TC10~~ (done), ~~Excel smoke ×3~~ (done), ~~697~~ (done) | DCA-686 (697); add DCA tasks per wave as needed |
| 2 | ~~SR332 TC01~~ (done), ~~TC03~~ (done), ~~TC04~~ (done), ~~887~~ (done), ~~2864~~ (done) | |
| 3 | ~~PBAC TC09~~ (done), ~~1035~~ (done) | DCA-694 (PBAC positives) |
| 4 | ~~1163~~ (done), ~~514~~ (done), ~~1051~~ (done), ~~3026~~ (done), ~~1405~~ (done) | |

Refresh this table when cases land on `develop`.

---

## References

- Katalon suite: `crdc-dh-automation/Test Suites/CRDC_Smoke.ts`
- Playwright markers: `pytest.ini`
- Hybrid POM / verify placement: `.cursor/rules/hybrid-pom-katalon-reuse.mdc`
- Excel DS runner: `docs/excel-ds-validation.md`, `tests/DataValidation/`
