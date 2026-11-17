# CRDC_Smoke port plan (Katalon → Playwright)

Goal: **`pytest -m CRDC_Smoke`** should cover the same Hub checks as Katalon **`Test Suites/CRDC_Smoke.ts`**, so the Playwright framework is useful for daily QA smoke without opening Katalon.

**Source of truth:** [`crdc-dh-automation/Test Suites/CRDC_Smoke.ts`](https://github.com/CBIIT/crdc-dh-automation/blob/develop/Test%20Suites/CRDC_Smoke.ts) (20 linked test cases, suite order below).

**Playwright command (target):** `pytest -m CRDC_Smoke` (optional `-n 4` after cookies are warm; run **`CRDC_PBAC`** setup serial when PBAC cases are included).

---

## Opinion: is full smoke worth it?

**Yes.** Today Playwright smoke is **Manage Studies (TC08)**, **Manage Programs (TC09)**, **Data Submissions list (TC10)**, **Submission Requests list (TC12)**, **PBAC TC09** (Submitter checked permissions), **CRDCDH-697 TC01** (headers), **CRDCDH-332 TC01** (SR all fields through submit), **TC03 / TC04** (DS list sorting and pagination, Dcp), and **887 TC101 / 2864 TC102** (Upload Errors modal). Katalon smoke is a **breadth slice**: list pages, SR create, table UX, PBAC functional check, and many DS paths (upload, validate, batch errors, cross-val, export, explorer). Porting it makes Playwright the credible pre-release gate Katalon smoke already is.

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
| 10 | `DataSubmissions/GC/CRDCDH-1163/TC16_...SubmittedMetadata` | Submitter (+ DCP flow in script) | **Not ported** | **Hard** | Create, upload, validate, **submit**, DCP validation path. Long workflow; uses PBAC/create helpers. |
| 11 | `DataSubmissions/GC/CRDCDH-1051/TC25_VerifyDcpCrossValidation` | Submitter, Dcp | **Not ported** | **Hard** | **Two** submissions, same study, cross-validate, CV tab TSV, reject. **`switch_user`**, cross-val UI, expected TSV oracles. |
| 12 | `DataSubmissions/GC/CRDCDH-514/TC06_VerifyFullDataSubmissionHistory` | Submitter | **Not ported** | **Hard** | ~147 lines: unique metadata upload, validate, history/audit assertions, **`prepareUniqueMetadataAndUpload`**. |
| 13 | `DataSubmissions/GC/CRDCDH-1035/TC101_VerifyValidationResultsExportAllRoles` | Submitter, Dcp, Fedlead, Admin | **Not ported** | **Hard** | Create + upload + validate; then **four roles** open same submission by ID, VR tab **export** + filename check. Needs deep-link nav + download assertion. |
| 14 | `DataSubmissions/GC/CRDCDH-887/TC101_ColumnRequiredBatchErrors` | Submitter | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-887/test_TC101_CRDCDH-887_ColumnRequiredBatchErrors.py` (`CRDC_Smoke`, `CRDC_DataValidation`, `CRDC_Regression`). Create a GC metadata-only submission, `upload_folder("CRDCDH-887_TC101")`, then `verify_upload_activities_batch_row("Metadata", 5, "Failed")` and `verify_upload_errors_modal`. Input folder copied from Katalon. Run live on QA2 (passes; one transient backend 'Batch loading failed' on a first 2864 run). Not yet dual-run against Katalon. |
| 15 | `DataSubmissions/GC/CRDCDH-2864/TC102_BatchErrorsCompositeIdRequiredProperty` | Submitter | **Done** | — | `tests/DataSubmissions/GC/CRDCDH-2864/test_TC102_CRDCDH-2864_BatchErrorsCompositeIdRequiredProperty.py` (same markers). Same flow with `CRDCDH-2864_TC102` and 4 files. Run live on QA2 (passes; one transient backend 'Batch loading failed' on a first 2864 run). Not yet dual-run against Katalon. |
| 16 | `DataSubmissions/GC/CRDCDH-1405/TC101_CLINoFileIdVerifyFinalManifest` | Submitter | **Not ported** | **Very hard** | **`CliUploader.uploadFilesViaCli`**, **`verifyFinalManifest`**, deterministic re-run. **No CLI layer in PW.** |
| 17 | `DataSubmissions/GC/CRDCDH-686-Partial/TC03_VerifyInvalidStrPtrn-IncompibleConsCode` | Submitter | **Done** | — | Workbook **`tests/DataValidation/GC/CRDCDH-686-Partial/TC03_....xlsx`** + runner **`verify_validation_results`**. `CRDC_Smoke` via collector allowlist (`_SMOKE_CASE_STEMS`). |
| 18 | `DataSubmissions/CTDC/.../TC101_...LongFormErrorsCTDC` | Submitter (Excel Settings) | **Done** | — | Workbook under `tests/DataValidation/CTDC/CRDCDH-699-CTDC/`. `CRDC_Smoke` via collector allowlist. On 2026-11-16 the Hub moved to CTDC 4.3.0 before STS had values for it (the nightly MDB promotion and the Hub PV puller had not run), so participant `radiology_report_available` (CDE-linked, no list in the model file) was not value-checked and the participant expected TSV was removed from smoke so the case does not depend on STS. The original `NO1` participant check lives in non-smoke, PW-only `TC104_CRDCDH-699_VerifyCdePermissibleValueErrorsCTDC` (not in Katalon). `Value not permitted` is now asserted on a second specimen record `ctdc_spec_2` with an invalid `specimen_type` (the VR table labels a record with its first issue, so each issue type needs its own record). Katalon's copy of `CRDCDH-699_TC101` needs the same edits. |
| 19 | `DataSubmissions/ICDC/.../TC36_...RequiredRelatedPropertyMissingICDC` | Submitter (Excel Settings) | **Done** | — | Workbook under `tests/DataValidation/ICDC/CRDCDH-699-ICDC/`. `CRDC_Smoke` via collector allowlist. |
| 20 | `DataSubmissions/GC/CRDCDH-3026/TC201_VerifyDataExplorerMetadataView` | Submitter | **Not ported** | **Hard** | **Data Explorer** page + TSV oracles; **QA seed** study `automation_CompletedStudy` (manual prereq). New page module. |

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
9. **CRDCDH-1035 TC101** VR export all roles (`switch_user`, submission deep link, download).

### Wave 4 — Heavy DS / CLI / Explorer

10. **CRDCDH-1163 TC16**, **CRDCDH-1051 TC25**, **CRDCDH-514 TC06**.
11. **CRDCDH-1405 TC101** (CLI + manifest — likely last).
12. **CRDCDH-3026 TC201** Data Explorer (new screen + env seed doc).

---

## Per-case analysis (what blocks each port)

### Auxiliary list tests (TC10, TC12, TC08, TC09)

| Case | Katalon keywords | Playwright gap |
|------|------------------|----------------|
| TC08/09 | Studies/Programs list | **Done** |
| TC10 | `DataSubmissionsList.*` | **Done** — `DataSubmissionsListPage` filters (name, status multi-select, program, submitter, commons, dbGaP), `read_table_rows`, `reset_filters` |
| TC12 | `SubmissionRequestList.*` | **Done** — `SubmissionRequestsListPage` filters/reset plus `read_table_rows`, `read_table_headers`, `start_button` |

**Next step:** Wave 3 — CRDCDH-1035 TC101 (VR export for all roles: `switch_user`, submission deep link, download check).

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

**Not ported:** cross-validation tab, VR export download, CLI, submission history timeline.

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

Update **`README.md`** / **`onboarding.md`** when smoke is complete: today they still say smoke is **TC08 + TC09 only**.

**Suggested CI job (future):**

```bash
pytest -m CRDC_PBAC -k EnableAllPermissions   # optional, serial
pytest -m CRDC_Smoke --tracing=retain-on-failure
```

---

## Tracking

| Wave | Cases | Owner / ticket |
|------|-------|----------------|
| 1 | ~~TC12~~ (done), ~~TC10~~ (done), ~~Excel smoke ×3~~ (done), ~~697~~ (done) | DCA-686 (697); add DCA tasks per wave as needed |
| 2 | ~~SR332 TC01~~ (done), ~~TC03~~ (done), ~~TC04~~ (done), ~~887~~ (done), ~~2864~~ (done) | |
| 3 | ~~PBAC TC09~~ (done), 1035 | DCA-694 (PBAC positives) |
| 4 | 1163, 1051, 514, 1405, 3026 | |

Refresh this table when cases land on `develop`.

---

## References

- Katalon suite: `crdc-dh-automation/Test Suites/CRDC_Smoke.ts`
- Playwright markers: `pytest.ini`
- Hybrid POM / verify placement: `.cursor/rules/hybrid-pom-katalon-reuse.mdc`
- Excel DS runner: `docs/excel-ds-validation.md`, `tests/DataValidation/`
