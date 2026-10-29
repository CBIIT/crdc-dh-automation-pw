# Excel-driven Data Submission validation

This framework is the **preferred way to add metadata-only Data Submission validation (VR) tests** in this repo. Each case is one Excel workbook under `tests/DataValidation/` that drives the same Hub flow as the Python tests—create submission, upload TSVs, validate, compare Validation Results to expected files—**without writing Groovy or Python test code**.

It is aimed at **QA engineers**: you supply **different datasets** (upload TSVs + expected Validation Results) and a **Steps** sheet; automation handles login (from Meta `role`), navigation, and oracle comparison via `validation_results.py`.

**`tests/DataValidation/`** — Excel cases only. **`tests/DataSubmissions/`** — Python flows and **reference** implementations (e.g. TC08) that stay runnable when Excel mode is off.

Canonical Python equivalent (same behavior): [`tests/DataSubmissions/GC/test_TC08_CRDC-VerifyInvalidIntegerValue.py`](../tests/DataSubmissions/GC/test_TC08_CRDC-VerifyInvalidIntegerValue.py).

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

```bash
# Loader/runner unit tests (no browser)
pytest tests/unit/test_excel_ds_loader.py -m unit

# All enabled Excel cases
pytest tests/DataValidation -m CRDC_DataValidation_Excel

# One case by name
pytest tests/DataValidation -m CRDC_DataValidation_Excel -k TC09
```

Hub credentials for the Meta **role** must be set in `config/qa.yaml` like any other UI test.

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
pytest tests/unit/test_excel_ds_loader.py -m unit

pytest tests/DataValidation -m CRDC_DataValidation_Excel

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
