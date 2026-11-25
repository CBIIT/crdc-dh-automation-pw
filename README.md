# crdc-dh-automation-pw

Playwright Python test framework for **CRDC Data Hub**. It is a behavior-preserving port of [`crdc-dh-automation`](../crdc-dh-automation) (Katalon / Selenium / Groovy), moved suite by suite. A Katalon suite is retired only after its Playwright version matches it on the same profile.

**New to the team?** Start at **[docs/onboarding.md](docs/onboarding.md)** (setup, core pieces: conftest / auth / config / hub / pages, how to run tests, and what the port is aiming for). The map of those files is **Core pieces** in that doc. Background and phases: [`ai/crdc/Playwright-Migration-Plan.md`](../../ai/crdc/Playwright-Migration-Plan.md).

## What is ported

| Area | Marker(s) | Where | State |
|---|---|---|---|
| Smoke | `CRDC_Smoke` | spread across the folders below | All 20 cases linked in Katalon `CRDC_Smoke.ts` are ported and audited against Katalon |
| Auxiliary | `CRDC_Auxiliary` | `tests/AuxiliaryTests/` | 6 of 13 runnable Katalon cases, plus PW-only Release Notes (CRDCDH-4006), six-role login (TC18) and SDM (CRDCDH-4027). Backlog: [docs/auxiliary-suite-port-plan.md](docs/auxiliary-suite-port-plan.md) |
| PBAC | `CRDC_PBAC` | `tests/Pbac/`, `tests/SuiteSetup/` | TC01-TC05 defaults, TC06-TC10 positives, TC11-TC15 negatives, then EnableAll. Manage-scope (TC16-TC17) and notifications are deferred |
| Data Submissions | `CRDC_DSFlow`, `CRDC_DataFileUpload` | `tests/DataSubmissions/GC/` | 10 cases: headers, batch errors, data file size and MD5, cross validation, validation after submit, export, history, Data Explorer view, and the upload CLI (CRDCDH-1405) |
| Data validation | `CRDC_DataValidation_Excel` | `tests/DataValidation/` | 15 cases for GC, ICDC and CTDC, defined as TSV (Excel also works); see [docs/excel-ds-validation.md](docs/excel-ds-validation.md) |
| Submission Requests | `CRDC_SubmissionRequests` | `tests/SubmissionRequest/` | CRDCDH-332 TC01, CRDCDH-3948 TC01-TC04, CRDCDH-3952 TC01 |

**Not ported yet:** notification emails, GraphQL/API cases, the Mongo case, the rest of the Auxiliary backlog, and the remaining Data Submissions and Submission Request cases. Run `pytest --collect-only -q -m <marker>` to see exactly what a marker selects.

## Requirements

- Python 3.11+
- Chromium (installed via Playwright)

## Setup

```bash
cd crdc-dh-automation-pw
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
# optional: ruff and mypy (not required to run tests)
# pip install -e ".[dev]"
playwright install chromium
cp config/qa.yaml.example config/qa.yaml
```

Fill `config/qa.yaml` from the matching Katalon profile (`AdminEmail`, `AdminPassword`, `AdminSecret`, plus Fedlead / Dcp / Submitter / User / Master). Same idea as `Profiles/CRDC_QA.glbl`: one file holds the Hub URL and the Login.gov accounts.

Use `dev` or `qa2` the same way (`cp config/qa2.yaml.example config/qa2.yaml`). Pick which file with `CRDC_PROFILE` (default `qa`):

```bash
CRDC_PROFILE=qa pytest -m CRDC_Auxiliary
```

`config/dev.yaml`, `qa.yaml`, and `qa2.yaml` are gitignored. Do not commit them.

## Run tests

Unit tests (no browser, no credentials; they use the committed `*.yaml.example` files):

```bash
pytest tests/unit -m unit
```

Live Hub tests use the same suite names as Katalon (`CRDC_Auxiliary`, `CRDC_PBAC`, `CRDC_Smoke`, `CRDC_Regression`, `CRDC_SubmissionRequests`, `CRDC_DSFlow`, `CRDC_DataValidation`). A case can carry more than one marker (TC08 is Auxiliary and Smoke). Notes:

- **PBAC is serial.** Run any selection that contains PBAC tests (Smoke, Regression, PBAC) without `-n`.
- **CLI case** (CRDCDH-1405 TC101) needs `SubmitterApiToken` in your `config/<profile>.yaml` and Python 3.13 or newer. It fails, not skips, without the token.
- **Data Explorer TC201** needs the `automation_CompletedStudy` study seeded on the environment.
- `ci/run_suite.sh <marker>` runs a suite the way CI does (EnableAll before and after); see [ci/README.md](ci/README.md).

```bash
pytest -m CRDC_Auxiliary
pytest -m CRDC_Auxiliary --headed
pytest -m CRDC_Smoke
pytest -m CRDC_PBAC   # TC01–TC05 defaults, TC06–TC10 positives, TC11–TC15 negatives, then EnableAll (serial; no -n)
pytest -m CRDC_SubmissionRequests -k 3948
```

Data validation cases (one `TC*.tsv` per case under `tests/DataValidation/`; see [docs/excel-ds-validation.md](docs/excel-ds-validation.md)):

```bash
pytest tests/DataValidation -m CRDC_DataValidation_Excel
pytest tests/DataValidation -m CRDC_DataValidation_Excel -k TC08
```

Every run writes a timestamped HTML report to `reports/report-YYYYMMDD-HHMMSS.html` (gitignored). Pass `--html=...` to override the path. Failed live tests attach a full-page screenshot to that report (and `reports/screenshots/`). They also keep a Playwright trace of the Hub tab under `test-results/` (gitignored); open it with `playwright show-trace test-results/.../trace.zip`.

Optional lint (does not run on `git commit`):

```bash
pip install -e ".[dev]"
ruff check src tests
mypy src/crdc_pw
```

## Layout

```
config/          # *.yaml.example committed; dev.yaml / qa.yaml / qa2.yaml gitignored
locators/CRDC/   # YAML object repository (Katalon paths preserved)
src/crdc_pw/     # loader, config, auth, hub, pages, utils
tests/unit/      # no browser
tests/AuxiliaryTests/  # live Hub cases (Katalon area folders, without a CRDC/ prefix)
tests/Pbac/      # TC01–TC05 defaults; TC06–TC10 positives; TC11–TC15 UncheckedPermissions
tests/SuiteSetup/  # EnableAllPermissions (CRDC_PBAC restore, Master)
tests/DataSubmissions/   # DS flow cases by ticket folder (GC/CRDCDH-####/)
tests/DataValidation/    # TSV-defined metadata validation cases (GC|ICDC|CTDC/<ticket>/TC*.tsv)
tests/SubmissionRequest/ # SR form and list cases by ticket folder
InputFiles/CRDC/ # PBACPermissions.xlsx, MetadataData/<case>/ upload + expected TSVs
docs/            # onboarding, validation framework, port plans
tools/           # crdc-datahub-cli-uploader (used by the CLI case)
auth/            # storage_state JSON (gitignored)
ci/              # GitHub Actions helper that writes the gitignored yaml from secrets
```

Look up a locator with the Katalon path:

```python
hub.locators.get("CRDC/AILocators/Global/Header/Desktop/UserName-Btn")
```

## Auth `storage_state`

After a successful Login.gov login, Playwright saves cookies to `auth/<profile>/<Role>.json`. A file lock next to that json means only one process OTPs a given account at a time. Later tests load the file into a new context and go to Hub; they do not re-check the header on every case. If the cookie died, one retry rewrites the json. Parallel is opt-in and must exclude PBAC: `pytest -m 'CRDC_Smoke and not CRDC_PBAC' -n 4`.

PBAC positives use `PBACPermissions.xlsx` columns `{Role}-positive` and the shared functional handlers; negatives use `{Role}-negative` and inverted PASS (`correctly *not* accessible`). Email/notification keys remain skipped. `pytest -k UncheckedPermissions` leaves Fedlead/Dcp/Submitter/User optional boxes unchecked (TC13 restores Admin). Run EnableAll before positives or smoke; full `pytest -m CRDC_PBAC` ends with EnableAll. Live PBAC runs need an Approved SR visible to each tested role, Submitted/In Review SRs for reviewer roles, and the GC `ATS - AutoTest-Study` study plus PBAC metadata files for the applicable DS checks. Offline checks establish workbook selection and test collection, not live permission behavior. Manage-scope (TC16–TC17) and notifications remain deferred.

## CI

See [ci/README.md](ci/README.md). The workflow in `.github/workflows/ci.yml` runs on `workflow_dispatch` only for now: the `unit` job (ruff, mypy, unit tests) always runs, and the live `smoke` job runs when you tick `run_smoke` and pick a profile. Checkout never contains the gitignored yaml files; unit tests use the examples, and the smoke job writes `config/<profile>.yaml` from GitHub Environment secrets before pytest.
