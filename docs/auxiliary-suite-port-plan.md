# CRDC_Auxiliary port plan (Katalon → Playwright)

Goal: **`pytest -m CRDC_Auxiliary`** should cover the same Hub checks as Katalon **`Test Suites/CRDC_Auxiliary.ts`**, so the Auxiliary suite can run without opening Katalon.

**Source of truth:** [`crdc-dh-automation/Test Suites/CRDC_Auxiliary.ts`](https://github.com/CBIIT/crdc-dh-automation/blob/develop/Test%20Suites/CRDC_Auxiliary.ts): 14 linked test cases, 13 with `isRun=true` (TC11 Mongo is linked but `isRun=false`).

**Playwright command (target):** `pytest -m CRDC_Auxiliary` (serial; the create/edit cases write Hub data and should not run in parallel with each other).

**Approach (same as Smoke):** port one Katalon case per change, keep the Katalon case id in the test file name, put DOM work in page objects and pure compares in `utils/`, and dual-run against Katalon on the same profile before marking a row **Done**.

---

## Katalon `CRDC_Auxiliary` order vs Playwright status

| # | Katalon test case | Role(s) | PW status | Difficulty | Notes |
|---|-------------------|---------|-----------|------------|-------|
| 1 | `AuxiliaryTests/TC04_PaginationVerification` | Dcp | **Done** | — | `tests/AuxiliaryTests/test_TC04_DSPaginationVerification.py` (also `CRDC_Smoke`). |
| 2 | `AuxiliaryTests/TC02_DeleteNodeFromDataView` | Submitter | To do | Medium | Wave 2. Data View page object is new. |
| 3 | `AuxiliaryTests/TC03_TableSortingVerification` | Dcp | **Done** | — | `tests/AuxiliaryTests/test_TC03_DSTableSortingVerification.py` (also `CRDC_Smoke`). |
| 4 | `AuxiliaryTests/TC11_MongoDBQuerySubmissions` | — (DB only) | Out of scope | High | `isRun=false` in Katalon; POC with a hardcoded Stage submission id. See "Out of scope". |
| 5 | `AuxiliaryTests/TC10_DataSubmissionsListAndFilter` | Submitter | **Done** | — | Also `CRDC_Smoke`. |
| 6 | `AuxiliaryTests/TC12_SubmissionRequestsListAndFilter` | Submitter | **Done** | — | Also `CRDC_Smoke`. |
| 7 | `AuxiliaryTests/TC05_DeleteRowsFromDataView` | Submitter | To do | Medium | Wave 2. Shares the Data View page object with TC02. |
| 8 | `AuxiliaryTests/TC08_ManageStudiesListAndFilter` | Admin | **Done** | — | Also `CRDC_Smoke`. |
| 9 | `AuxiliaryTests/CRDCDH-3913/TC01_CRDCDH-3913_ManageStudiesCsvExport` | Admin, Fedlead | To do | Medium | Wave 1. Read-only (no Hub writes); new export locators and a CSV oracle. |
| 10 | `AuxiliaryTests/TC09_ManageProgramsListAndFilter` | Admin | **Done** | — | Also `CRDC_Smoke`. |
| 11 | `AuxiliaryTests/TC16_EditExistingProgram` | Admin | To do | Medium | Wave 3. Katalon edits a hardcoded program; port must be self-contained. |
| 12 | `AuxiliaryTests/TC15_CreateNewProgram` | Admin | To do | Low | Wave 3. Program form page object is new. |
| 13 | `AuxiliaryTests/TC14_EditExistingStudy` | Admin | To do | Medium | Wave 3. Katalon edits a hardcoded study; port must be self-contained. |
| 14 | `AuxiliaryTests/TC13_CreateNewStudy` | Admin | To do | Low | Wave 3. Study form page object is new. |

**Already `CRDC_Auxiliary` in Playwright but not in the Katalon suite** (keep them; they are not part of the port count):

- `test_TC18_LoginAllRolesAndSwitchUser.py`: Katalon `TC18` exists in the AuxiliaryTests folder but is not linked in `CRDC_Auxiliary.ts`.
- `test_TC_CRDCDH-4006_ReleaseNotesPage.py`: PW-only (Xray CRDCDH-4006).

**Status:** 6 of 13 runnable cases done (all six are the Smoke overlap). 7 to port.

---

## Recommended port waves (easiest first)

### Wave 1 — Read-only export (no Hub writes)

1. **CRDCDH-3913 TC01** Manage Studies CSV export (Admin, then Fedlead).

Exit criteria: export UI states (enabled and empty) and CSV contents are checked for both roles, with no data created.

### Wave 2 — Data View deletes (Submitter, own submission)

2. **TC02** Delete node from Data View.
3. **TC05** Delete rows from Data View.

Both create their own submission, so they are safe to run repeatedly. One page object serves both.

Exit criteria: `DataSubmissionDetailPage` (or a new `DataViewPage`) can select a node, select rows, delete, and wait for the deletion to finish, and each test asserts the result.

### Wave 3 — Manage Studies / Manage Programs create and edit (Admin, writes Hub data)

4. **TC15** Create new program.
5. **TC16** Edit existing program (creates its own program first, then edits it).
6. **TC13** Create new study.
7. **TC14** Edit existing study (creates its own study first, then edits it).

Exit criteria: `ProgramFormPage` and `StudyFormPage` fill, save and read back fields; each test leaves behind only data it created, with timestamped names.

### Not planned

- **TC11** Mongo query (see "Out of scope").

---

## Per-case analysis

### CRDCDH-3913 TC01 — Manage Studies CSV export (Wave 1)

Katalon flow and checks (all from `utilities.ManageStudies`):

| Step | Katalon | Check |
|------|---------|-------|
| 1 | `navigateToManageStudies`, `verifyManageStudiesListPage` | Container, Add Study, table present (same as TC08) |
| 2 | `verifyManageStudiesExportUiWhenHasData` | Export button visible and enabled; tooltip `Export the current list of Studies to CSV.` |
| 3 | Filter study name `CRDCDH3913-no-match-<millis>`, `verifyManageStudiesExportUiWhenEmpty` | Pagination total is 0; Export disabled; tooltip `No results to export. No studies match your filters.` |
| 4 | Reset, then filter `autoQA` / `AutoTest-Program` / `Active` / `Open` | Table total > 0 |
| 5 | If total > 10, rows per page 10 | (setup so the CSV must hold more rows than the visible page) |
| 6 | `clickManageStudiesExportAndVerifyDownloadedFileName` + three CSV checks | File name `crdc-manage-studies-YYYY-MM-DD-HH-mm-ss.csv`; headers exactly `Name, Acronym, dbGaPID, Access Type, Principal Investigator, ORCID, Program, Data Concierge, Status, Created Date` (no `Action`); data rows equal the UI total; every row's Name or Acronym contains `autoQA` (ignore case) |
| 7 | `switchUser('Fedlead')`, open Manage Studies, export UI when has data | Same as step 2 for Fedlead |
| 8 | Fedlead exports the default list | File name, headers, data rows equal the UI total |

Playwright pieces:

- **Reuse:** `StudiesListPage.open`, `apply_filters` (name, program, status, access type already exist), `read_table_rows`, `switch_user`, `verify_tooltip_on_hover_page`, `assert_button_enabled`, `BasePage` pagination (`verify_rows_per_page_change` code path to set 10 rows, displayed-rows text parse in `utils/table_helpers.parse_displayed_rows` for the total).
- **Add locators:** `Studies/List/ExportStudies-Btn` and `Studies/List/ExportStudies-Tooltip` (exist in the Katalon Object Repository, not yet in `locators/`). Re-run the locator conversion or add them by hand.
- **Add to `StudiesListPage`:** `export_button`, `export_tooltip`, `reset_filters` (Katalon defaults: empty name and dbGaP, program All, status Active, access All), `table_total()` (Katalon `getTableTotalEntryCount`), `export_csv() -> Path` (Playwright download event, as in 1035 TC101; no Downloads folder clearing).
- **New pure module** `utils/manage_studies_export.py`: `check_export_filename`, `EXPECTED_MANAGE_STUDIES_CSV_HEADERS`, `diff_export_headers`, `count_csv_data_rows`, `rows_missing_token(csv, token)` (Name or Acronym, case-insensitive). Use `csv` module parsing (quoted cells), with unit tests.
- **Test:** `tests/AuxiliaryTests/CRDCDH-3913/test_TC01_CRDCDH-3913_ManageStudiesCsvExport.py`, `hub` = Admin, then `switch_user(hub, "Fedlead")`.

Data dependency: QA needs at least one study matching `autoQA` + `AutoTest-Program` + `Active` + `Open` (the same fixture TC08 uses).

### TC02 / TC05 — Delete from Data View (Wave 2)

Katalon flows:

- **TC02:** Submitter, `Pbac.createDataSubmission` (ATS study, metadata only), `prepareUniqueMetadataAndUpload(PBAC/program.tsv, program_acronym)`, then `deleteNodeFromDataView('program')`: Data View tab, Node Type = program, header checkbox, Delete, confirm dialog, wait up to 120 s for `DeletionAlert` to go away.
- **TC05:** same create, `uploadMetadataUI(PBAC/participant.tsv)` (200 rows), then `deleteRowsFromDataView('participant', 37)`: Data View, Node Type = participant, rows per page = 50 (first option ≥ 37), tick the first 37 row checkboxes, Delete, confirm, wait up to 60 s for `DeletionAlert`.

**Katalon asserts nothing after the delete.** The keyword only fails on an exception, and `waitForElementNotVisible` on the alert also passes if the alert never appeared. Porting it exactly would give a test that cannot catch a broken delete.

Recommendation (PW-only tightening, noted in the test docstring like the other PW extras):

- TC02: after deletion, the program node has 0 rows in Data View (empty table, or the node is gone from the Node Type options). Optionally the Data View node count / Summary stats drop.
- TC05: record the participant total before (displayed-rows text, 200), delete 37, assert the total is 163.

Playwright pieces:

- **Reuse:** `DataSubmissionsListPage.create_data_submission`, `prepare_unique_program_tsv`, `DataSubmissionDetailPage.upload_metadata_file`, `BasePage` rows-per-page change, `parse_displayed_rows`.
- **Locators already converted:** `DataSubmissions/Detail/Tabs/DataView-Tab`, `DataView/Filters/NodeType-Ddn`, `DataView/Filters/DeleteNodeData-Btn`, `DataView/HeaderCheckbox-Chkbx`, `DataView/RowCheckbox-Chkbx`, `DataView/DeletionAlert`, `DeleteDialog/Dialog` and `Confirm-Btn`.
- **New:** Data View methods, either on `DataSubmissionDetailPage` or a small `DataViewPage` (preferred: the detail page is already large): `open_data_view`, `select_node(node)`, `select_all_rows`, `select_first_rows(n)`, `delete_selected_and_confirm`, `wait_deletion_done(timeout)` (wait for the alert to appear **and** then disappear, or wait on the row count), `node_total()`.
- **Input:** `InputFiles/CRDC/MetadataData/PBAC/participant.tsv` is already in PW and identical to Katalon's (200 data rows).
- **Tests:** `tests/AuxiliaryTests/test_TC02_DeleteNodeFromDataView.py`, `tests/AuxiliaryTests/test_TC05_DeleteRowsFromDataView.py`.

Reuse later: the CRDCDH-1382 "deleted record" cases (Katalon `CRDCDH-1382-*`) delete from Data View too and can use the same page object.

### TC15 / TC16 — Create and edit program (Wave 3)

Katalon:

- **TC15** `addNewProgram()`: Add Program, name `autoQA-Program-<yyyyMMdd-HHmmss>`, abbreviation `autoQA-<ts>`, Save. Passes if `This program has been successfully added.` appears. **If the duplicate-name error appears instead it cancels and returns without failing** (only a ValidationReport Fail row). Fails if neither message appears.
- **TC16** `editExistingProgram('AutoProgram-TC15-10', [abbreviation, description with timestamp, status Active])`: filter by name, Edit on the matching row, fill only those fields, Save, wait for the list. **No read-back check**, and the program name is hardcoded, so it depends on an earlier manual run.

Recommendation:

- TC15: duplicate name is a failure in PW (names are timestamped, so a duplicate means something is wrong). Also filter the list by the new name and assert one row, which Katalon does for studies but not programs.
- TC16: create a program in the test (TC15 helper), edit it, then reopen Edit (or read the list row) and assert abbreviation, description and status. No hardcoded program name.

Playwright pieces:

- **Reuse:** `ProgramsListPage.open`, `apply_filters(program_name=)`, `read_table_rows`.
- **Locators already converted:** `Programs/List/AddProgram-Btn`, `Programs/Detail/*` (name, abbreviation, description, data concierge, status, Save, Cancel, success and duplicate messages).
- **New:** `pages/program_form.py` `ProgramFormPage`: `fill(name=, abbreviation=, description=, data_concierge=, status=, only_provided=)` (Katalon `fillProgramForm`; read it for the dropdown handling), `save`, `cancel`, `read_fields()`. `ProgramsListPage.add_program_click`, `edit_row(name)` (match exact cell, then Katalon's truncated-prefix fallback).
- **Tests:** `tests/AuxiliaryTests/test_TC15_CreateNewProgram.py`, `tests/AuxiliaryTests/test_TC16_EditExistingProgram.py`.

### TC13 / TC14 — Create and edit study (Wave 3)

Katalon:

- **TC13** `addNewStudy()`: Add Study, name `autoQA-Study-<ts>`, acronym `autoQA-<ts>`, GPA `Auto-GPA`, program `auto_program`, access Open, dbGaP `phs000001`, Save, filter by name, assert at least one row.
- **TC14** `editExistingStudy('AutoStudy-TC13-6', [acronym 'Edited-Existing-3', accessTypes 'Open Access', program 'Not Applicable'])`: filter, Edit, fill, Save, wait for the list. **No read-back check**, hardcoded study name.

Recommendation:

- TC13: as Katalon, plus assert the row's acronym and program.
- TC14: create a study in the test, edit it (timestamped acronym, program `Not Applicable`, access Open), then assert the list row (acronym, program, access type). No hardcoded study name. Note the Katalon `accessTypes: 'Open Access'` value relies on `fillStudyForm` matching "open"; read `fillStudyForm` (ManageStudies.groovy line 232) for the checkbox and Program dropdown rules before porting.

Playwright pieces:

- **Reuse:** `StudiesListPage.open`, `apply_filters`, `read_table_rows`, and the `edit_row(name)` helper shape from programs.
- **Locators already converted:** `Studies/List/AddStudy-Btn`, `Studies/Detail/*` (name, abbreviation, GPA, PI, ORCID, dbGaP, program, open/controlled access, same-as-program concierge, pending conditions, Save, Cancel).
- **New:** `pages/study_form.py` `StudyFormPage` with `fill(..., only_provided=)`, `save`, `read_fields()`.
- **Tests:** `tests/AuxiliaryTests/test_TC13_CreateNewStudy.py`, `tests/AuxiliaryTests/test_TC14_EditExistingStudy.py`.

Data dependency: program `auto_program` must exist on the target environment (Katalon hardcodes it).

---

## Out of scope

| Case | Why | If it is wanted later |
|------|-----|-----------------------|
| **TC11 MongoDBQuerySubmissions** | `isRun=false` in the suite; POC with a hardcoded Stage submission id (`0ff5bf86-…`) and the `released` query from `DBQueries`; needs `G_MongoUri` per profile. PW has no Mongo client. | Add `pymongo`, `MongoUri` / `MongoDatabase` to `config/<profile>.yaml` (gitignored, never committed), a `utils/mongo.py` that loads the query template, and port the real users first (`DatabaseUtils.verifyRecordsExistInMongoForSubmission` in the 1405 TC102 cases) rather than this POC. |
| **TC17 VisionScreenshotComparison** | Not linked in `CRDC_Auxiliary.ts`; Jenkins-only SSIM baseline compare through `CompareScreenshotToBaseline.py`. | Separate decision: Playwright element screenshot plus the same SSIM script, or a snapshot plugin. Baselines are machine-specific. |

---

## Shared work and cross-cutting rules

- **Names:** every created submission, study and program is timestamped so runs never collide and no cleanup is needed (same as Katalon).
- **Downloads:** use Playwright's download event (as 1035 TC101), not a Downloads folder.
- **No ValidationReport:** checks are assertions; failures list every mismatch.
- **PW-only tightening** (Data View result checks, program/study read-back, duplicate program name fails) is noted in each test's docstring and in the row above, so a dual-run difference is expected, not a regression.
- **Markers:** every ported case gets `CRDC_Auxiliary`. Do not add `CRDC_Smoke` or `CRDC_Regression`.

---

## Tracking

| Wave | Cases | Owner / ticket |
|------|-------|----------------|
| Done | TC03, TC04, TC08, TC09, TC10, TC12 (Smoke overlap) | |
| 1 | CRDCDH-3913 TC01 | |
| 2 | TC02, TC05 | |
| 3 | TC15, TC16, TC13, TC14 | |
| Out | TC11 (Mongo), TC17 (not in suite) | |

Refresh this table when cases land on `develop`. Delete this file when every wave is done, as was done for the Smoke plan.

---

## References

- Katalon suite: `crdc-dh-automation/Test Suites/CRDC_Auxiliary.ts`
- Katalon keywords: `Keywords/utilities/ManageStudies.groovy`, `ManagePrograms.groovy`, `DataSubmissions.groovy` (`deleteNodeFromDataView`, `deleteRowsFromDataView`), `WebUIUtils.groovy` (`getTableTotalEntryCount`, `changeRowsPerPage`)
- Playwright markers: `pytest.ini`
- Hybrid POM / verify placement: `.cursor/rules/hybrid-pom-katalon-reuse.mdc`
