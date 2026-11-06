# CRDC_Smoke port plan (Katalon → Playwright)

Goal: **`pytest -m CRDC_Smoke`** should cover the same Hub checks as Katalon **`Test Suites/CRDC_Smoke.ts`**, so the Playwright framework is useful for daily QA smoke without opening Katalon.

**Source of truth:** [`crdc-dh-automation/Test Suites/CRDC_Smoke.ts`](https://github.com/CBIIT/crdc-dh-automation/blob/develop/Test%20Suites/CRDC_Smoke.ts) (20 linked test cases, suite order below).

**Playwright command (target):** `pytest -m CRDC_Smoke` (optional `-n 4` after cookies are warm; run **`CRDC_PBAC`** setup serial when PBAC cases are included).

---

## Opinion: is full smoke worth it?

**Yes.** Today Playwright smoke is only **Manage Studies (TC08)** and **Manage Programs (TC09)** plus **CRDCDH-697 TC01** (headers) on the feature branch. Katalon smoke is a **breadth slice**: list pages, SR create, table UX, PBAC functional check, and many DS paths (upload, validate, batch errors, cross-val, export, explorer). Porting it makes Playwright the credible pre-release gate Katalon smoke already is.

**Pragmatic approach:** work **top to bottom of the Katalon suite list** for traceability, but **implement in difficulty tiers** (below) so early merges add value without blocking on CLI or multi-role epics.

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
| 1 | `AuxiliaryTests/TC10_DataSubmissionsListAndFilter` | Submitter | **Not ported** | **Easy** | ~53-line script: nav, list chrome, filters, reset. **`DataSubmissionsListPage`** has `open()` + create; **missing** list filter/reset/read/verify helpers (mirror `DataSubmissionsList` keywords). |
| 2 | `SubmissionRequest/CRDCDH-332/TC01_CRDC_Submission_Request-AllFields` | Submitter | **Partial** | **Medium** | **`SubmissionRequestFormPage.fill_submission_request_all_sections`** exists; smoke needs full A–D fill + submit path from Katalon TC01 (Excel/input if any). Not the same as CRDCDH-3948 Save tests. |
| 3 | `AuxiliaryTests/TC12_SubmissionRequestsListAndFilter` | Submitter | **Partial** | **Easy** | **`SubmissionRequestsListPage`**: `open`, `apply_submission_requests_list_filters`, `reset_submission_requests_filters`. Add test: chrome + filter + assert row count (TC08 shape). |
| 4 | `AuxiliaryTests/TC08_ManageStudiesListAndFilter` | Admin | **Done** | — | `tests/AuxiliaryTests/test_TC08_ManageStudiesListAndFilter.py` |
| 5 | `AuxiliaryTests/TC09_ManageProgramsListAndFilter` | Admin | **Done** | — | `tests/AuxiliaryTests/test_TC09_ManageProgramsListAndFilter.py` |
| 6 | `AuxiliaryTests/TC03_TableSortingVerification` | Dcp | **Not ported** | **Medium** | DS list: sortability, default sort, click-sort columns. Needs **generic table helpers** on `BasePage` or `utils/` (Katalon `WebUIUtils.verifyTableColumnSortability`, etc.) — **none in PW yet**. |
| 7 | `AuxiliaryTests/TC04_PaginationVerification` | Dcp | **Not ported** | **Medium** | DS list pagination: rows/page options, default, navigation, change page size. Same **generic table** gap as TC03. |
| 8 | `Pbac/TC09_CRDC-PbacCheckedPermissions-Submitter` | Admin → Submitter | **Partial** | **Medium** | **TC01 Fedlead** pattern exists (`pbac_sheet`, `ManageUsersPage`). TC09: Admin sets Submitter **positive** permissions, logout/login, **`verifyPermissionsFunctional`**. Need functional PBAC keyword port (nav + action checks), not just checkbox sheet. |
| 9 | `DataSubmissions/GC/CRDCDH-697/TC01_CRDC-VerifyDataSubmissionHeaders` | Submitter | **Done** (PR) | — | `tests/DataSubmissions/GC/CRDCDH-697/...` |
| 10 | `DataSubmissions/GC/CRDCDH-1163/TC16_...SubmittedMetadata` | Submitter (+ DCP flow in script) | **Not ported** | **Hard** | Create, upload, validate, **submit**, DCP validation path. Long workflow; uses PBAC/create helpers. |
| 11 | `DataSubmissions/GC/CRDCDH-1051/TC25_VerifyDcpCrossValidation` | Submitter, Dcp | **Not ported** | **Hard** | **Two** submissions, same study, cross-validate, CV tab TSV, reject. **`switch_user`**, cross-val UI, expected TSV oracles. |
| 12 | `DataSubmissions/GC/CRDCDH-514/TC06_VerifyFullDataSubmissionHistory` | Submitter | **Not ported** | **Hard** | ~147 lines: unique metadata upload, validate, history/audit assertions, **`prepareUniqueMetadataAndUpload`**. |
| 13 | `DataSubmissions/GC/CRDCDH-1035/TC101_VerifyValidationResultsExportAllRoles` | Submitter, Dcp, Fedlead, Admin | **Not ported** | **Hard** | Create + upload + validate; then **four roles** open same submission by ID, VR tab **export** + filename check. Needs deep-link nav + download assertion. |
| 14 | `DataSubmissions/GC/CRDCDH-887/TC101_ColumnRequiredBatchErrors` | Submitter | **Not ported** | **Medium** | Upload fail → **`verifyUploadActivitiesBatchRow`** + **`verifyUploadActivitiesFailedErrorsModal`**. Detail page has VR/oracles; **batch upload error modal** keywords not ported. |
| 15 | `DataSubmissions/GC/CRDCDH-2864/TC102_BatchErrorsCompositeIdRequiredProperty` | Submitter | **Not ported** | **Medium** | Same shape as 887 (different folder `CRDCDH-2864_TC102`). Share one port for batch-error modal pattern. |
| 16 | `DataSubmissions/GC/CRDCDH-1405/TC101_CLINoFileIdVerifyFinalManifest` | Submitter | **Not ported** | **Very hard** | **`CliUploader.uploadFilesViaCli`**, **`verifyFinalManifest`**, deterministic re-run. **No CLI layer in PW.** |
| 17 | `DataSubmissions/GC/CRDCDH-686-Partial/TC03_VerifyInvalidStrPtrn-IncompibleConsCode` | Submitter | **Excel only** | **Easy*** | Workbook **`tests/DataValidation/GC/CRDCDH-686-Partial/TC03_....xlsx`** + runner **`verify_validation_results`**. *Easy = add **`CRDC_Smoke`** marker to collected test (or one pytest wrapper), not rewrite script. |
| 18 | `DataSubmissions/CTDC/.../TC101_...LongFormErrorsCTDC` | (Excel Settings) | **Excel only** | **Easy*** | Workbook under `tests/DataValidation/CTDC/...`. Mark **`CRDC_Smoke`** on Excel collection. |
| 19 | `DataSubmissions/ICDC/.../TC36_...RequiredRelatedPropertyMissingICDC` | (Excel Settings) | **Excel only** | **Easy*** | Workbook under `tests/DataValidation/ICDC/...`. Mark **`CRDC_Smoke`**. |
| 20 | `DataSubmissions/GC/CRDCDH-3026/TC201_VerifyDataExplorerMetadataView` | Submitter | **Not ported** | **Hard** | **Data Explorer** page + TSV oracles; **QA seed** study `automation_CompletedStudy` (manual prereq). New page module. |

**Out of scope for Katalon smoke (already noted in suite description):** API token tests CRDCDH-1551/1526.

---

## Recommended port waves (easiest first)

Use this order for **implementation**, while keeping **Katalon case IDs** in test names/paths.

### Wave 1 — List smoke + Excel smoke (high value, low new infra)

1. **TC12** Submission Requests list + filter (`SubmissionRequestsListPage`).
2. **TC10** Data Submissions list + filter (extend **`DataSubmissionsListPage`**).
3. **CRDCDH-686 TC03**, **CRDCDH-699 CTDC TC101**, **CRDCDH-699 ICDC TC36** — expose on **`CRDC_Smoke`** via Excel runner markers (document `pytest -m "CRDC_Smoke and CRDC_DataValidation_Excel"` overlap or unify markers).
4. Merge **CRDCDH-697 TC01** (headers).

**Exit criteria:** Submitter can exercise three list pages (SR, DS, Studies/Programs already done) + one DS create + three validation smokes without new Katalon.

### Wave 2 — SR smoke + table UX + batch upload errors

5. **CRDCDH-332 TC01** SR AllFields (extend form page orchestration).
6. **TC03** table sorting + **TC04** pagination (shared generic table API on DS list).
7. **CRDCDH-887 TC101** + **CRDCDH-2864 TC102** (shared upload-activities failed-modal verifier).

### Wave 3 — PBAC + multi-role DS

8. **PBAC TC09** Submitter checked permissions (functional verify).
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
| TC10 | `DataSubmissionsList.*` | Filter fields (name, status, program, submitter, commons), `readDataSubmissionsListTableRows`, reset |
| TC12 | `SubmissionRequestList.*` | Filter + **test** asserting `expectAtLeastRows` (page has apply/reset) |

**Easiest next step:** TC12 test file mirroring TC08 (~40 lines).

### Generic table (TC03, TC04)

Katalon centralizes in **`WebUIUtils`**: sortability, default sort, column click sort, pagination options, page nav, rows-per-page change.

Playwright: add locators under **`CRDC/AILocators/GenericTable/`** (if missing) and methods on **`BasePage`** or a small **`utils/table_helpers.py`** used by DS list tests. **One port serves both** TC03 and TC04.

### PBAC TC09 vs Playwright TC01

| | Katalon TC09 | Playwright today |
|---|--------------|------------------|
| Setup | Admin `editPbacPermissions('Submitter', 'positive')` | TC01: Admin reset/compare **Fedlead** sheet |
| Verify | Submitter `verifyPermissionsFunctional` | No functional PBAC runner in PW |

Port needs **`verify_permissions_functional(role, scenario)`** (or split by resource) plus locators for actions PBAC gates.

### DS validation / upload (686, 699, detail page)

**Already on `DataSubmissionDetailPage`:** `upload_folder`, `click_validate`, `verify_validation_results_vs_expected_for_tc`, error details.

**Not ported:** upload-activities batch row status, failed-errors modal (887/2864), cross-validation tab, VR export download, CLI, submission history timeline.

### Excel vs native pytest for smoke

| Approach | Pros | Cons |
|----------|------|------|
| Native pytest per Katalon `.tc` | Clear 1:1, `CRDC_Smoke` on one file | Duplicates Excel for TC03/686 if both exist |
| Excel collector + `CRDC_Smoke` marker | Reuses **`step_runner`** | Smoke job runs Excel loader; role from workbook Settings |

**Recommendation:** For **686/699 CTDC/ICDC** rows in smoke, **mark existing Excel tests** with `CRDC_Smoke` and list them in this doc. For **887/2864/1035**, prefer **native pytest** until/unless you add Excel workbooks.

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
| 1 | TC12, TC10, Excel smoke ×3, 697 | DCA-686 (697); add DCA tasks per wave as needed |
| 2 | SR332 TC01, TC03, TC04, 887, 2864 | |
| 3 | PBAC TC09, 1035 | |
| 4 | 1163, 1051, 514, 1405, 3026 | |

Refresh this table when cases land on `develop`.

---

## References

- Katalon suite: `crdc-dh-automation/Test Suites/CRDC_Smoke.ts`
- Playwright markers: `pytest.ini`
- Hybrid POM / verify placement: `.cursor/rules/hybrid-pom-katalon-reuse.mdc`
- Excel DS runner: `docs/excel-ds-validation.md`, `tests/DataValidation/`
