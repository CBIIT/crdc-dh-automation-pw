# Excel-driven Data Submission validation

This framework allows Excel-driven test cases for Data Submission validation. Each case is one Excel workbook under `tests/DataValidation/` that creates submission, uploads TSVs, validates, and compares Validation Results to expected files—**without writing Groovy or Python test code**.

It is aimed at **QA engineers**: you supply **different datasets** (another **data commons** (GC, ICDC, CTDC, …), another **study**, upload TSVs + expected Validation Results) and the **Steps** sheet; automation handles login (from Settings `role`), navigation, and comparison.

`tests/DataValidation/` — Excel-driven data validation cases only.
`tests/DataSubmissions/` — Other DS lifecycle tests.

---

## Run

| Goal | Command |
|------|---------|
| Run all Excel test cases | `pytest tests/DataValidation -m CRDC_DataValidation_Excel` |
| Run a specific test case | `pytest tests/DataValidation -m CRDC_DataValidation_Excel -k TC09` |

Add `--headed` to watch the browser.

---

## Add a new test case

1. **Copy** `tests/DataValidation/GC/TC08_CRDCDH-686_VerifyInvalidIntegerValue.xlsx` → `tests/DataValidation/<model>/TC09_CRDCDH-###_<Scenario>.xlsx` (must start with **TC**; include ticket id for traceability, e.g. **CRDCDH-686**).
2. **Copy** `InputFiles/CRDC/MetadataData/TC08/` → `MetadataData/TC09/` (or your case id). Replace upload `*.tsv` and files under `expected-ValidationResults/`.
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
| create_data_submission | New | metadata only | GC | autoQA - AutomationQA_Study | |
| upload_metadata_folder | `<caseId>` | |
| click_validate | | |
| verify_validation_results_for_tc | `<caseId>` | `GC` |

- **create_data_submission:** four fields in **Params**, separated by `|` e.g. `New|metadata only|GC|autoQA - AutomationQA_Study`.
- **verify_validation_results_for_tc:** case id in **Params**, commons in **Model** (GC, ICDC, CTDC).

**Settings** (tab 2): `role`, `enabled` (Y/N). Workbook run settings—not `config/qa.yaml`.

**TSV naming (upload + expected):** Put upload files in the case folder root (not under `expected-ValidationResults/`). Use the same pattern as TC08—`<model>_<node>_v<version>.tsv` (example: `GC_diagnosis_v11.0.3.tsv`). For each node you assert in Validation Results, add a matching file under **`expected-ValidationResults/`** named `<model>_<node>_v<version>_expected-ValidationResults.tsv` (example: `GC_diagnosis_v11.0.3_expected-ValidationResults.tsv`). When adding a case, copy an existing folder for your model and change file contents only; keep upload and expected names paired the same way TC08 does.

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
     upload step    │                             │ verify step
     reads *.tsv    │                             │ scrapes Validation Results tab
                    ▼                             ▼
         ┌──────────────────────┐      ┌───────────────────────┐
         │ MetadataData/<case>/ │      │ validation_results.py │
         │ upload TSVs          │      │                       │
         │ expected-VR/*.tsv ───┼─────►│ UI vs expected TSVs   │
         └──────────────────────┘      └───────────────────────┘
```
