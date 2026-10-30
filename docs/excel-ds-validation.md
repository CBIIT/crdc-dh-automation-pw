# Excel-driven Data Submission validation

This framework allows Excel-driven test cases for Data Submission validation. Each case is one Excel workbook under `tests/DataValidation/` that creates submission, uploads TSVs, validates, and compares Validation Results to expected files—**without writing Groovy or Python test code**.

It is aimed at **QA engineers**: you supply **different datasets** (another **data commons** (GC, ICDC, CTDC, …), another **study**, upload TSVs + expected Validation Results) and the **Steps** sheet; automation handles login (from Settings `role`), navigation, and comparison.

`**tests/DataValidation/**` — Excel-driven data validation cases only. 
`**tests/DataSubmissions/**` — Other DS lifecycle tests.

## How it works

Each `**TC*.xlsx**` has **Steps** (Hub actions) and **Settings** (`role`, `enabled`).

```
                         ┌──────────────────────┐
                         │  pytest + conftest   │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │               test_collector              │
              │  tests/DataValidation/**/TC*.xlsx         │
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
     upload step    │                             │ verify step
     reads *.tsv    │                             │ scrapes Validation Results tab
                    ▼                             ▼
         ┌──────────────────────┐      ┌──────────────────────┐
         │ MetadataData/<case>/ │      │ validation_results   │
         │ upload TSVs          │      │ .py                  │
         │ expected-VR/*.tsv ───┼─────►│ UI vs expected TSVs  │
         └──────────────────────┘      └──────────────────────┘
```

---

## Run

| Goal | Command |
|------|---------|
| Run all Excel test cases | `pytest tests/DataValidation -m CRDC_DataValidation_Excel` |
| Run a specific test case | `pytest tests/DataValidation -m CRDC_DataValidation_Excel -k TC09` |

Add `**--headed**` to watch the browser.

---

## Add a new test case

1. **Copy** `tests/DataValidation/GC/TC08_CRDC-VerifyInvalidIntegerValue.xlsx` → `tests/DataValidation/<model>/TC09_<name>.xlsx` (name must start with `**TC`**).
2. **Copy** `InputFiles/CRDC/MetadataData/TC08/` → `MetadataData/TC09/` (or your case id). Replace upload `*.tsv` and files under `**expected-ValidationResults/`**.
3. **Edit Settings** (2nd tab): `role` = e.g. **Submitter**; `enabled` = **Y** (or **N** while drafting).
4. **Edit Steps** (1st tab): row 2 = input root e.g. `InputFiles/CRDC/MetadataData/TC09`; update create/upload/verify rows for your **study**, **model**, and folder name (see [Workbook format](#workbook-format)).
5. **Run** using command above.

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
| create_data_submission | `New\|metadata only\|GC\|autoQA - AutomationQA_Study` | |
| upload_metadata_folder | `<caseId>` | |
| click_validate | | |
| verify_validation_results_for_tc | `<caseId>` | `GC` |

- **create_data_submission:** `New\|metadata only\|<model>\|<study label>` (pipe-separated).
- **verify_validation_results_for_tc:** case id in **Params**, commons in **Model** (GC, ICDC, CTDC).

**Settings** (tab 2): `role`, `enabled` (Y/N). Workbook run settings—not `config/qa.yaml`.

Expected VR file naming follows `**DSV_ValidationResults-mappings.xlsx**` per model; see `validation_results.py` if needed.

---

## Where to change things (developers)

| Need | Location |
|------|----------|
| Enable/disable Excel collection | `config/*.yaml` → `excel_ds_validation.enabled` (or `CRDC_EXCEL_DS_VALIDATION=1`) |
| Case workbook (Steps + Meta) | `tests/DataValidation/<model>/TC*.xlsx` |
| Upload + expected VR files | `InputFiles/CRDC/MetadataData/<case>/` |
| Step actions | `src/crdc_pw/utils/excel_ds_test_runner/step_runner.py` |
| Pytest collection | `excel_ds_test_runner/test_collector.py` (plugin in `tests/conftest.py`) |
| VR compare rules | `validation_results.py` |
