# crdc-dh-automation-pw

Playwright Python test framework for **CRDC Data Hub**. This is a behavior-preserving port of [`crdc-dh-automation`](../crdc-dh-automation) (Katalon / Selenium / Groovy).

**New to the team?** Start at **[docs/onboarding.md](docs/onboarding.md)** (setup, core pieces — conftest / auth / config / hub / pages — how to run tests, and what the port is aiming for). The map of those files is **Core pieces** in that doc.

Phase 0 is the scaffold plus the first live cases: YAML object repository, profile config, Login.gov OTP, auth `storage_state`, six-role login smoke, TC08/TC09 lists, TC01 PBAC Fedlead, and CRDCDH-3974 Release Notes. Remaining suites are later phases. See [`ai/crdc/Playwright-Migration-Plan.md`](../../ai/crdc/Playwright-Migration-Plan.md).

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

Use `qa2` or `stage` the same way (`cp config/qa2.yaml.example config/qa2.yaml`). Pick which file with `CRDC_PROFILE` (default `qa`):

```bash
CRDC_PROFILE=qa pytest -m CRDC_Auxiliary
```

`config/qa.yaml`, `qa2.yaml`, and `stage.yaml` are gitignored. Do not commit them.

## Run tests

Unit tests (no browser, no credentials; they use the committed `*.yaml.example` files):

```bash
pytest tests/unit -m unit
```

Live Hub tests use the same suite names as Katalon (`CRDC_Auxiliary`, `CRDC_PBAC`, `CRDC_Smoke`). `CRDC_Smoke` is only the Katalon smoke subset (TC08 and TC09 today), not every live case. TC18 (six-role login) is Auxiliary, not Smoke.

```bash
pytest -m CRDC_Auxiliary
pytest -m CRDC_Auxiliary --headed
pytest -m CRDC_Smoke
pytest -m CRDC_PBAC
```

Excel Data Validation (`.xlsx` under `tests/DataValidation/`; see [docs/excel-ds-validation.md](docs/excel-ds-validation.md)):

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
config/          # *.yaml.example committed; qa.yaml / qa2.yaml / stage.yaml gitignored
locators/CRDC/   # YAML object repository (Katalon paths preserved)
src/crdc_pw/     # loader, config, auth, hub, pages, utils
tests/unit/      # no browser
tests/AuxiliaryTests/  # live Hub cases (Katalon area folders, without a CRDC/ prefix)
tests/Pbac/      # TC01 PBAC defaults
auth/            # storage_state JSON (gitignored)
ci/              # GitHub Actions helper that writes the gitignored yaml from secrets
```

Look up a locator with the Katalon path:

```python
hub.locators.get("CRDC/AILocators/Global/Header/Desktop/UserName-Btn")
```

## Auth `storage_state`

After a successful Login.gov login, Playwright saves cookies to `auth/<profile>/<Role>.json`. A file lock next to that json means only one process OTPs a given account at a time. Later tests load the file into a new context and go to Hub; they do not re-check the header on every case. If the cookie died, one retry rewrites the json. Parallel (opt-in, not default): `pytest -m CRDC_Smoke -n 4`.

## CI

See [ci/README.md](ci/README.md). GitHub Actions is a placeholder (`workflow_dispatch` only) until the repo is on GitHub. Checkout never contains the gitignored yaml files; unit tests use the examples, and smoke jobs write `config/<profile>.yaml` from GitHub Environment secrets before pytest.
