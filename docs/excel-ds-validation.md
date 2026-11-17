# Excel-driven Data Submission validation

This framework allows Excel-driven test cases for Data Submission validation. Each case is one Excel workbook under `tests/DataValidation/` that creates submission, uploads TSVs, validates, and compares Validation Results to expected files—**without writing Groovy or Python test code**.

It is aimed at **QA engineers**: you supply **different datasets** (another **data commons** (GC, ICDC, CTDC, …), another **study**, upload TSVs + expected Validation Results) and the **Steps** sheet; automation handles login (from Settings `role`), navigation, and comparison.

`tests/DataValidation/` — Excel-driven data validation cases only. Layout mirrors Katalon: `tests/DataValidation/<GC|ICDC|CTDC>/<ticket-folder>/TC##_....xlsx` (e.g. `GC/CRDCDH-686-Partial/TC08_...`).
`tests/DataSubmissions/` — Other DS lifecycle tests.

---

## Run

| Goal | Command |
|------|---------|
| Run all Excel test cases | `pytest tests/DataValidation -m CRDC_DataValidation_Excel` |
| Run all in parallel (shared Submitter) | `pytest tests/DataValidation -m CRDC_DataValidation_Excel -n 4` |
| Run a specific test case | `pytest tests/DataValidation -m CRDC_DataValidation_Excel -k TC09` |

Add `--headed` to watch the browser. Create step assigns a **25-character** name `auto-test_yyyyMMdd_HHxxxx` (`xxxx` = random hex for parallel runs; Hub truncates longer names).

---

## Add a new test case

1. **Copy** `tests/DataValidation/GC/CRDCDH-686-Partial/TC08_CRDCDH-686_VerifyInvalidIntegerValue.xlsx` → `tests/DataValidation/<model>/<ticket-folder>/TC09_CRDCDH-###_<Scenario>.xlsx` (mirror Katalon `Test Cases/CRDC/DataSubmissions/...`; name must start with **TC**).
2. **Copy** `InputFiles/CRDC/MetadataData/TC08/` → `MetadataData/TC09/` (or your case id). Replace upload `*.tsv` and files under `expected-ValidationResults/` and update the data as needed.
3. In the test case, edit **Settings** (2nd tab): `role` = e.g. **Submitter**; `enabled` = **Y** (or **N** while drafting).
4. Edit **Steps** (1st tab): row 2 = input root e.g. `InputFiles/CRDC/MetadataData/TC09`; update create/upload/verify rows for your **study**, **model**, and folder name (see [Workbook format](#workbook-format)).
5. Save all workbook changes and run the test case.

---

## Workbook format

**Steps** (tab 1) — row 1 header: `Input Excel | Action | Params | Model`

| Row | Content |
|-----|---------|
| 2 | `InputFiles/CRDC/MetadataData/<caseId>` |
| 3+ | Actions in order (typical VR flow below) |

| Action | Params | Model |
|--------|--------|-------|
| open_data_submissions | | |
| create_data_submission | New | metadata only | GC | autoQA - AutomationQA_Study | |
| upload_metadata_folder | `<caseId>` | |
| click_validate | | |
| verify_error_details | `<caseId>` | `GC` |
| verify_validation_results | `<caseId>` | `GC` |

- **create_data_submission:** four fields in **Params**, separated by `|` e.g. `New|metadata only|GC|autoQA - AutomationQA_Study`.
- **verify_error_details:** (optional) same **Params** / **Model** as `verify_validation_results`. Opens **See details** on Validation Results rows and checks the error-details dialog against `Expected_Issues` (or `Issue_Type`) in the same `expected-ValidationResults/*.tsv` files. **CRDCDH-686-Partial** workbooks omit this step (Katalon table-only).
- **verify_validation_results:** case id in **Params**, commons in **Model** (GC, ICDC, CTDC). Compares the aggregated Validation Results table to expected TSVs.

**Settings** (tab 2): `role`, `enabled` (Y/N). Workbook run settings—not `config/qa.yaml`.

**Smoke membership:** Workbooks that are in the Katalon `CRDC_Smoke` suite also get the `CRDC_Smoke` marker. The list is `_SMOKE_CASE_STEMS` in `src/crdc_pw/utils/excel_ds_test_runner/test_collector.py` (file name without `.xlsx`). Today: 686-Partial TC03, 699 CTDC TC101, 699 ICDC TC36. To add a workbook, add its stem to that set; a unit test fails if a stem has no committed workbook. Run them with `pytest -m "CRDC_Smoke and CRDC_DataValidation_Excel"`.

**PW-only case, not smoke:** `TC104_CRDCDH-699_VerifyCdePermissibleValueErrorsCTDC` (input `InputFiles/CRDC/MetadataData/CRDCDH-699_TC104/`) is the original CTDC TC101 data. It expects `Value not permitted` for participant `radiology_report_available = NO1`. That property is linked to a CDE and has no list in the model file, so its values come from STS. The case fails whenever STS does not yet have values for the Hub's current CTDC model version (for example the day a new version is merged to `develop`, before the nightly MDB promotion and the Hub's PV puller). Katalon has no TC104. Run it with `pytest -k TC104_CRDCDH-699`.

**TSV naming (upload + expected):** Put upload files in the case folder root (not under `expected-ValidationResults/`). Use the same pattern as TC08—`<model>_<node>_v<version>.tsv` (example: `GC_diagnosis_v11.0.3.tsv`). For each node you assert in Validation Results, add a matching file under `expected-ValidationResults/` named `<model>_<node>_v<version>_expected-ValidationResults.tsv` (example: `GC_diagnosis_v11.0.3_expected-ValidationResults.tsv`). When adding a case, copy an existing folder for your model and change file contents only; keep upload and expected names paired the same way TC08 does.

A test is available to check your test cases are written in the right format **(Steps/Settings are correct)**:

```bash
pytest tests/unit/test_excel_ds_loader.py -m unit
```

---

## How it works

Each `TC*.xlsx` has **Steps** (Hub actions) and **Settings** (`role`, `enabled`).

```
                         ┌──────────────────────┐
                         │  pytest + conftest   │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │               test_collector              │
              │     tests/DataValidation/**/TC*.xlsx      │
              └─────────────────────┬─────────────────────┘
                                    │
                         ┌──────────▼────────────┐
                         │loader (Steps/Settings)│
                         └──────────┬────────────┘
                                    │
                         ┌──────────▼───────────┐
                         │     step_runner      │  each Step action
                         └──────────┬───────────┘
                                    │
         ┌──────────────────────────▼───────────────────────────┐
         │ Hub fixture (role) + DS list/detail page objects     │
         │ Playwright drives CRDC Hub (create, upload, validate)│
         └──────────┬─────────────────────────────┬─────────────┘
                    │                             │
     upload step    │                             │ verify steps
     reads *.tsv    │                             │ VR tab + See details + table
                    ▼                             ▼
         ┌──────────────────────┐      ┌───────────────────────┐
         │ MetadataData/<case>/ │      │ validation_results.py │
         │ upload TSVs          │      │                       │
         │ expected-VR/*.tsv ───┼─────►│ dialog + table oracles│
         └──────────────────────┘      └───────────────────────┘
```
