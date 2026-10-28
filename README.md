# crdc-dh-automation-pw

Playwright Python test framework for **CRDC Data Hub**. This is a behavior-preserving port of [`crdc-dh-automation`](../crdc-dh-automation) (Katalon / Selenium / Groovy).

**New to the team?** Start at **[docs/onboarding.md](docs/onboarding.md)** (setup, how the framework works, how to run tests, and what the port is aiming for).

Phase 0 is the scaffold: YAML object repository, profile config, Login.gov OTP, auth `storage_state`, and a six-role login smoke. PBAC and the rest of the suites are later phases. See [`ai/crdc/Playwright-Migration-Plan.md`](../../ai/crdc/Playwright-Migration-Plan.md).

## Requirements

- Python 3.11+
- Chromium (installed via Playwright)

## Setup

```bash
cd crdc-dh-automation-pw
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
cp config/qa.yaml.example config/qa.yaml
```

Fill `config/qa.yaml` from the matching Katalon profile (`AdminEmail`, `AdminPassword`, `AdminSecret`, plus Fedlead / Dcp / Submitter / User / Master). Same idea as `Profiles/CRDC_QA.glbl`: one file holds the Hub URL and the Login.gov accounts.

Use `qa2` or `stage` the same way (`cp config/qa2.yaml.example config/qa2.yaml`). Pick which file with `CRDC_PROFILE` (default `qa`):

```bash
CRDC_PROFILE=qa pytest -m smoke
```

`config/qa.yaml`, `qa2.yaml`, and `stage.yaml` are gitignored. Do not commit them.

## Run tests

Unit tests (no browser, no credentials; they use the committed `*.yaml.example` files):

```bash
pytest tests/unit -m unit
```

Live login smoke (Katalon TC18, `tests/AuxiliaryTests/test_TC18_LoginAllRolesAndSwitchUser.py`): Admin, Fedlead, Dcp, Submitter, User, and Master. Each role writes `auth/<profile>/<role>.json`. A role is skipped if its yaml values are blank.

```bash
pytest -m smoke
pytest -m smoke --headed
```

Every run writes a timestamped HTML report to `reports/report-YYYYMMDD-HHMMSS.html` (gitignored). Pass `--html=...` to override the path. Failed live tests attach a full-page screenshot to that report (and `reports/screenshots/`).

## Layout

```
config/          # *.yaml.example committed; qa.yaml / qa2.yaml / stage.yaml gitignored
locators/CRDC/   # YAML object repository (Katalon paths preserved)
src/crdc_pw/     # loader, config, auth, hub, pages, utils
tests/unit/      # no browser
tests/AuxiliaryTests/  # live Hub cases (Katalon area folders, without a CRDC/ prefix)
auth/            # storage_state JSON (gitignored)
ci/              # GitHub Actions helper that writes the gitignored yaml from secrets
```

Look up a locator with the Katalon path:

```python
hub.locators.get("CRDC/AILocators/Global/Header/Desktop/UserName-Btn")
```

## Auth `storage_state`

After a successful Login.gov login, Playwright saves cookies to `auth/<profile>/<role>.json`. Later tests reuse that file so they do not pay OTP every time. The fixture still opens Hub and checks that the header username is visible; if the session expired it logs in again and overwrites the file.

## CI

See [ci/README.md](ci/README.md). GitHub Actions is a placeholder (`workflow_dispatch` only) until the repo is on GitHub. Checkout never contains the gitignored yaml files; unit tests use the examples, and smoke jobs write `config/<profile>.yaml` from GitHub Environment secrets before pytest.
