# Excel-driven Data Submission validation

This framework is the **preferred way to add metadata-only Data Submission validation (VR) tests** in this repo. Each case is one Excel workbook under `tests/DataValidation/` that drives the same Hub flow as the Python tests—create submission, upload TSVs, validate, compare Validation Results to expected files—**without writing Groovy or Python test code**.

It is aimed at **QA engineers**: you supply **different datasets** (upload TSVs + expected Validation Results) and a **Steps** sheet; automation handles login (from Meta `role`), navigation, and oracle comparison via `validation_results.py`.

**`tests/DataValidation/`** — Excel cases only. **`tests/DataSubmissions/`** — Python flows and **reference** implementations (e.g. TC08) that stay runnable when Excel mode is off.

Canonical Python equivalent (same behavior): [`tests/DataSubmissions/GC/test_TC08_CRDC-VerifyInvalidIntegerValue.py`](../tests/DataSubmissions/GC/test_TC08_CRDC-VerifyInvalidIntegerValue.py).

Katalon source of truth for the same flow lives in **`crdc-dh-automation`** under `Test Cases/CRDC/DataSubmissions/` (suite **`CRDC_DataValidation`**).

---

## Katalon cases you can add (same Steps flow)

Each row below is **metadata only**: create DS → upload TSVs → validate → compare Validation Results to **`expected-ValidationResults/`**. In Excel, that is the five Steps actions in [§4](#4-fill-sheet-steps-first-tab); only **model**, **study**, **upload folder**, and **verify Params/Model** change.

**Already in Playwright / Excel today:** GC **TC08** (`MetadataData/TC08`).

### GC — `CRDCDH-686-Partial` and `CRDCDH-699`

| Katalon test case | Typical `MetadataData` folder |
|-------------------|-------------------------------|
| TC03 `CRDC-VerifyInvalidStrPtrn-IncompibleConsCode` | `TC03` |
| TC07 `CRDC-VerifyOneToOneRelationshipConflict` | `TC07` |
| TC08 `CRDC-VerifyInvalidIntegerValue` | `TC08` |
| TC09 `CRDC-VerifyInvalidNumberValue` | `TC09` |
| TC10 `CRDC-VerifyStdyNamMismProgNamMismVluNotPerm` | `TC10` |
| TC20 `CRDC-VerifyRelatedNodeNotFound` | `TC20` |
| TC04 `CRDC-699-VerifyMissingRequiredProperty` | `TC04` |
| TC05 `CRDC-699-VerifyRelationshipNotSpecified` | `TC05` |

Study on most GC cases: **`autoQA - AutomationQA_Study`**. Upload and expected TSVs for these folders already exist in Katalon **`InputFiles/CRDC/MetadataData/`** (copy into this repo when adding a case).

Example Katalon paths (under `crdc-dh-automation`):

- `Test Cases/CRDC/DataSubmissions/GC/CRDCDH-686-Partial/TC08_CRDC-VerifyInvalidIntegerValue.tc`
- `Test Cases/CRDC/DataSubmissions/GC/CRDCDH-699/TC04_CRDC-699-VerifyMissingRequiredProperty.tc`
- `Test Cases/CRDC/DataSubmissions/ICDC/CRDCDH-699-ICDC/TC36_CRDC-699-RequiredRelatedPropertyMissingICDC.tc`
- `Test Cases/CRDC/DataSubmissions/CTDC/CRDCDH-699-CTDC/TC101_CRDC-699-VerifyValidationResultsLongFormErrorsCTDC.tc`

**Not the same thin flow** (keep as Python/Katalon until Steps grow): e.g. TC19/TC21 (`both` + data files), CRDCDH-1007, CRDCDH-1042, CRDCDH-3140, CRDCDH-3839 (Data View / `expected/`), CRDCDH-887 (Upload Activities), cross-validation multi-DS flows.

### ICDC — `CRDCDH-699-ICDC`

| Katalon test case | Typical `MetadataData` folder |
|-------------------|-------------------------------|
| TC35 `CRDC-699-InvalidDateIntegerPvICDC` | `TC35` |
| TC36 `CRDC-699-RequiredRelatedPropertyMissingICDC` | `TC36` |
| TC37 `CRDC-699-ControlledAccessOpenConsentCodeICDC` | `TC37` |

Workbook path: `tests/DataValidation/ICDC/TC35_....xlsx`. Steps: **`ICDC`** in create Params; **Model** column **`ICDC`** on verify.

### CTDC — `CRDCDH-699-CTDC`

| Katalon test case | Typical `MetadataData` folder |
|-------------------|-------------------------------|
| TC101 `CRDC-699-VerifyValidationResultsLongFormErrorsCTDC` | `CRDCDH-699_TC101` |
| TC103 `CRDC-699-VerifyValidationResultsConsentCodeErrorsCTDC` | `CRDCDH-699_TC103` |

Workbook path: `tests/DataValidation/CTDC/...`. Steps: **`CTDC`** model; verify **Model** = **`CTDC`**.

### Smoke sentinels (one per model)

Same pattern, often run in **`CRDC_Smoke`**: GC **686 TC03**, ICDC **699-ICDC TC36**, CTDC **699-CTDC TC101**.

### New datasets, not only Katalon clones

The Excel runner is not limited to porting the table above. QA can add **new combinations**—different upload TSVs, new expected VR files, another study label, or a new folder under `MetadataData/<YourCase>/`—to exercise validator rules without new Python. Copy the **TC08** workbook and data layout, change row 2 input root and Steps Params/Model, and commit the TSVs. That is the intended way to expand coverage beyond what Katalon already automates.

---

## Running Excel cases (QA)

**Before you run**

1. Repo root, Python venv activated (same setup as other Hub tests — see [onboarding.md](onboarding.md)).
2. Gitignored **`config/qa.yaml`** with Submitter (and other) credentials and **`excel_ds_validation.enabled: true`**.

**Simple commands** (recommended — no pytest flags to remember):

| Goal | Command |
|------|---------|
| All enabled Excel cases | `python scripts/run_excel_ds_validation.py` |
| One case (match workbook name) | `python scripts/run_excel_ds_validation.py TC09` |
| One case by description fragment | `python scripts/run_excel_ds_validation.py VerifyInvalidInteger` |
| Watch the browser | `python scripts/run_excel_ds_validation.py TC08 --headed` |

The script runs pytest for you with the correct folder and tags.

**pytest flags (optional)** — only if you run pytest directly:

- **`-m CRDC_DataValidation_Excel`** — “marker”: run tests tagged as Excel Data Validation (like Katalon suite filters). Other Hub tests are skipped.
- **`-k TC09`** — “keyword”: run tests whose name contains `TC09` (workbook stem, e.g. `TC09_CRDC-...`).

Equivalent manual commands:

```bash
pytest tests/DataValidation -m CRDC_DataValidation_Excel
pytest tests/DataValidation -m CRDC_DataValidation_Excel -k TC09
```

**Meta `enabled: N`** on a workbook skips collection (pytest never sees that file). **YAML `excel_ds_validation.enabled: false`** skips all Excel `.xlsx` collection.

---

## How to add a new test case

Follow these steps for a new case (example: **TC09**).

### 1. Prepare metadata and expected results

Under the repo root:

```text
InputFiles/CRDC/MetadataData/TC09/
  GC_*.tsv                          # files to upload (top level only)
  expected-ValidationResults/
    GC_*_expected-ValidationResults.tsv   # one expected file per node you assert
```

- Copy structure from **`InputFiles/CRDC/MetadataData/TC08/`** and change data for your scenario.
- Expected TSV naming and node mapping use **`InputFiles/CRDC/DataSubmissionValidation/DSV_ValidationResults-mappings.xlsx`** (model sheet, e.g. **GC**). See `src/crdc_pw/utils/validation_results.py` if you need column/node details.

### 2. Create the Excel workbook

**Path:** `tests/DataValidation/GC/TC09_<short-description>.xlsx`  
(Use **`TC`** prefix so pytest collects the file. Organize by model: `GC/`, later `CDS/`, etc.)

**Easiest start:** copy **`tests/DataValidation/GC/TC08_CRDC-VerifyInvalidIntegerValue.xlsx`**, rename, then edit the **Steps** and **Meta** sheets to match the format below.

### 3. Fill sheet **Meta** (second tab)

| key     | value |
|---------|--------|
| role    | Hub role for login, e.g. **`Submitter`** (must match a role in project config) |
| enabled | **`Y`** to collect and run; **`N`** while drafting (pytest skips the file) |

### 4. Fill sheet **Steps** (first tab)

**Row 1 (header, exact text):** `Input Excel | Action | Params | Model`

**Row 2:** repo-relative folder for this case’s upload data, e.g.  
`InputFiles/CRDC/MetadataData/TC09`

**Rows 3+:** one action per row, in order. Typical metadata-only VR flow:

| Action | Params | Model |
|--------|--------|-------|
| open_data_submissions | | |
| create_data_submission | `New\|metadata only\|GC\|autoQA - AutomationQA_Study` | |
| upload_metadata_folder | `TC09` | |
| click_validate | | |
| verify_validation_results_for_tc | `TC09` | `GC` |

**Params rules**

- **`create_data_submission`:** four fields separated by **`|`** — submission type, data type, **model** (e.g. GC), study label.
- **`upload_metadata_folder`:** folder name under the row 2 input root (usually the TC id, e.g. `TC09`).
- **`verify_validation_results_for_tc`:** TC id in **Params** (must match `MetadataData/<TC>`); **Model** column = mappings sheet name (e.g. **`GC`**).
- Other steps: leave Params and Model blank unless noted above.

**Supported actions only** (unknown actions fail with a clear error):

`open_data_submissions`, `create_data_submission`, `upload_metadata_folder`, `click_validate`, `verify_validation_results_for_tc`

### 5. Config

Committed profile examples include **`excel_ds_validation.enabled: true`**, so Excel cases under `tests/DataValidation/` are collected once you have a normal **`config/qa.yaml`** (copy from **`config/qa.yaml.example`**). Set **`enabled: false`** in your local yaml if you want to skip Excel collection without removing workbooks.

```yaml
excel_ds_validation:
  enabled: true
  excel_cases_glob: tests/DataValidation/**/*.xlsx
```

### 6. Run your case

See [Running Excel cases (QA)](#running-excel-cases-qa). Example after adding TC09:

```bash
python scripts/run_excel_ds_validation.py TC09
```

### 7. Commit checklist

- Workbook under `tests/DataValidation/...`
- New/changed files under `InputFiles/CRDC/MetadataData/<TC>/` and expected TSVs
- Do **not** commit `config/qa.yaml` (secrets)

---

## Workbook reference

**Tab order:** **Steps** first, **Meta** second.

### Meta

| key | value |
|-----|-------|
| role | Submitter (typical for DS VR) |
| enabled | Y / N |

### Steps

- Row 1: `Input Excel | Action | Params | Model`
- Row 2: metadata input root (directory must exist under repo when loaded)
- Row 3+: executable steps

---

## Run commands (summary)

```bash
# QA: Excel cases
python scripts/run_excel_ds_validation.py
python scripts/run_excel_ds_validation.py TC08

# Developers: loader unit tests (no browser)
pytest tests/unit/test_excel_ds_loader.py -m unit

# Python reference TC08 (not Excel)
pytest tests/DataSubmissions/GC/test_TC08_CRDC-VerifyInvalidIntegerValue.py -m CRDC_DataValidation
```

---

## How it works (developers)

| Piece | Role |
|-------|------|
| `src/crdc_pw/utils/excel_ds_test_runner/loader.py` | Parse Meta/Steps; `StepRow`, `ExcelLoadError` |
| `src/crdc_pw/utils/excel_ds_test_runner/step_runner.py` | Dispatch Steps → `DataSubmissionsListPage` / `DataSubmissionDetailPage` |
| `src/crdc_pw/utils/excel_ds_test_runner/test_collector.py` | One pytest test per `tests/DataValidation/**/TC*.xlsx` when enabled |
| `src/crdc_pw/utils/excel_ds_test_runner/config_helpers.py` | `excel_ds_validation` YAML + env flag |
| `tests/conftest.py` | `pytest_plugins = ["crdc_pw.utils.excel_ds_test_runner.test_collector"]` |

VR comparison is unchanged: page method → `validation_results.py` (expected TSVs + mappings). No duplicate oracle logic in the Excel package.
