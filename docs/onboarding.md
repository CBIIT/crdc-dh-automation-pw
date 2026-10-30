# QA onboarding — CRDC Data Hub Playwright tests

This is the starting point if you are new to **`crdc-dh-automation-pw`**. It covers what this repo is, how it works today, how to set it up and run tests, and what “done” looks like after we leave Katalon.

You do **not** need Katalon Studio installed to run this project. You do need a Hub QA account (or the shared automation accounts) and Python 3.11+.

---

## What this project is

CRDC Data Hub UI automation used to live in **`crdc-dh-automation`**: Katalon Studio, Groovy, Selenium. This repo is the replacement: **Python + pytest + Playwright**.

It is a **behavior-preserving port**, not a rewrite of the product under test:

- Same Hub environments (QA, QA2, Stage)
- Same Login.gov accounts and roles
- Same test intent, case IDs (`TC##_CRDCDH-…`), and input files (Excel / TSV) as we bring suites over
- New engine, locators stored as YAML, tests written as pytest

The sibling Katalon project is still the live suite until we cut over area by area. Do not freeze Katalon globally; a suite moves here when that slice is green.

---

## Where we are vs the end goal

### Today (Phase 0 — scaffold plus first cases)

The framework can:

- Load Hub URL and Login.gov credentials from one YAML file per environment
- Look up locators the same way Katalon did (`CRDC/Login/...`)
- Sign in through Login.gov with TOTP (one-time password)
- Reuse a saved browser session so the next run does not pay OTP every time
- Sign in as **Admin, Fedlead, Dcp, Submitter, User, and Master** and land on Hub (TC18)
- Run **TC08** Manage Studies, **TC09** Manage Programs, **TC01** PBAC Fedlead defaults, **CRDCDH-3974** Release Notes, and **TC08** GC invalid-integer Data Submission (metadata VR)

That is the floor everything else builds on. Submission Requests, remaining Data Submissions, emails, Mongo, and GraphQL are **not** here yet.

### End goal (after the port)

Replace the Katalon Hub suites with this repo so QA and CI run Playwright instead of Katalon:

| Area (Katalon today) | Rough size | Lands in this repo as |
|---|---:|---|
| Data Submissions | ~79 cases | `tests/` + DS page objects (largest slice) |
| Notification emails | ~27 | UI in Playwright; existing Gmail Python stays |
| Submission Requests | ~19 | SR form + list |
| PBAC | ~19 | First real suite after login |
| Admin / lists / aux | ~16 | Programs, Studies, institutions, dashboard |
| API | ~3 | GraphQL via HTTP, not the browser |

**Cutover rule:** dual-run a suite on QA until it matches Katalon, then retire that Katalon suite. Not a big-bang switch.

Planned order after this scaffold:

1. Remaining **PBAC defaults** (TC02–05) plus isolated PBAC tickets — TC01 is already here
2. **Shared UI helpers on BasePage** — tables, MUI dropdowns, snackbars (done; unblocks every list page)
3. **Submission Requests**
4. **Data Submissions** (upload, validate, results tables)
5. **Non-browser oracles** — Mongo, GraphQL, CLI uploader, Gmail (`utils/` already holds Excel and GitHub-raw helpers)
6. **Notifications and remaining admin**
7. **CI on GitHub Actions** for smoke + suites; Katalon retired suite by suite

If you are joining during the port, expect new tests to show up as pytest files that still mention the Katalon case name in a comment.

---

## How the framework is laid out

Every live Hub test uses the same pattern:

1. **Fixture** (`hub`) — open the browser, sign in as a role (Login.gov / saved cookies). Same idea as Katalon `closeBrowser` + `loginToCrdcOtp` at the top of every script, except it is not copied into each pytest file.
2. **Page** — one Hub screen. Locators stay in YAML; the page turns those paths into clicks, fills, and reads.
3. **Test** — the *scenario* plus asserts: construct the page, drive it, `expect` / `assert` in the pytest file.
4. **Utils** (optional) — Excel, GitHub raw, TOTP when the case is not page-only. Not a screen.

Initial login is **setup**, not a line in the test. **TC08** (Manage Studies list and filter) is the example below: construct a page, navigate, `expect`, filter, assert. PBAC and DS tests follow the same pattern after the same logged-in `hub`.

If login or the browser fails, follow the plumbing table below. If you want to know *what the case is testing*, read the pytest file.

### Core pieces

These files are the whole framework. Everything else is a page or a test that uses them.

```mermaid
flowchart TB
  pytestRun[pytest]
  conftest[conftest.py]
  configPy[config.py]
  configYaml[config/qa.yaml]
  loader[LocatorLoader]
  locYaml[locators YAML]
  authPy[auth.py]
  hubBag[Hub]
  testFile[test file]
  pageObj[pages]
  utilsBox[utils]
  pytestRun --> conftest
  conftest --> configPy
  configPy --> configYaml
  conftest --> loader
  loader --> locYaml
  conftest --> authPy
  authPy --> hubBag
  conftest --> hubBag
  hubBag --> testFile
  testFile --> pageObj
  pageObj --> loader
  testFile -.-> utilsBox
```

| Piece | File | Job in one sentence |
|---|---|---|
| **pytest** | you run this | Discovers tests and asks `conftest` for fixtures |
| **conftest** | `tests/conftest.py` | Setup for every live test: open browser, log in, HTML report, failure screenshot. Not a page. |
| **config** | `src/crdc_pw/config.py` + `config/qa.yaml` | Which Hub URL and which Login.gov accounts (was Katalon Profiles) |
| **locators** | `locators/CRDC/**/*.yaml` + `src/crdc_pw/locators/loader.py` | Katalon path → XPath (was Object Repository) |
| **auth** | `src/crdc_pw/auth.py` | Login.gov OTP / Grant, file-locked `storage_state`. Fixture only. Tests do not call this unless the *scenario* switches user |
| **hub** | `src/crdc_pw/hub.py` | Thin bag the fixture hands the test: this tab, this role, locators, settings. Not the Hub website |
| **pages** | `src/crdc_pw/pages/` | One Hub screen each (`StudiesListPage`, `HeaderPage`, …). Clicks and reads. `BasePage` holds locator resolve, Hub timeouts, and shared table / dropdown / snackbar helpers |
| **tests** | `tests/AuxiliaryTests/`, `tests/Pbac/`, `tests/DataSubmissions/`, `tests/DataValidation/` | Scenario + pass/fail. Same Katalon suite names (`CRDC_Auxiliary`, `CRDC_PBAC`, `CRDC_Smoke`, `CRDC_DataValidation`) |
| **utils** | `src/crdc_pw/utils/` | Optional oracles (Excel, TOTP, GitHub raw). Not a screen |

How one live test runs:

```mermaid
sequenceDiagram
  participant P as pytest
  participant C as conftest
  participant A as auth
  participant T as test
  participant PG as page
  P->>C: this test asked for hub
  C->>C: load qa.yaml and YAML locators
  C->>A: ensure_storage_state then land on Hub
  A-->>C: signed in on this tab
  C->>T: here is hub
  T->>PG: open filter read
  PG-->>T: rows or text
  T->>T: expect or assert
```

Adding TC12 does **not** mean editing conftest, hub, auth, or config. You add a page (if the screen is new) and a pytest file. Touch auth/conftest only when login or session setup is wrong.

### Layers (test author's view)

The files above collapse to four jobs when you write a case:

```mermaid
flowchart LR
  fixture["conftest builds hub"]
  test["test: scenario + asserts"]
  page["pages/"]
  yaml["locators YAML"]
  utils["utils/"]
  fixture --> test
  test --> page
  page --> yaml
  test -.-> utils
```

`hub` is who is signed in. The **test** owns the scenario and asserts. A **page** is one Hub screen. **utils** is optional: Excel, GitHub raw markdown, TOTP — not a screen.

### Folders

```
crdc-dh-automation-pw/
├── tests/                  # pytest files (Katalon Test Case / Script)
│   ├── conftest.py         # builds `hub`: browser + login  ← start here if login fails
│   ├── AuxiliaryTests/     # TC08 studies, TC09, TC18, CRDCDH-3974
│   ├── Pbac/               # TC01 Fedlead defaults
│   ├── DataSubmissions/    # DS flow / Python scenarios (e.g. TC08 reference)
│   ├── DataValidation/     # Excel workbook cases (Steps sheet); optional when flag on
│   └── unit/               # no browser (locator, config, sheet, notes helpers)
├── src/crdc_pw/
│   ├── hub.py              # thin session the fixture yields (page, locators, settings, role)
│   ├── auth.py             # Login.gov OTP / Grant (fixture only; tests do not call this)
│   ├── config.py           # which yaml file, which role credentials
│   ├── pages/              # login, header, studies, programs, users, data_submissions, release_notes
│   ├── locators/loader.py  # Katalon path → XPath string
│   └── utils/              # pbac_sheet, validation_results, static_content, otp
├── locators/CRDC/          # YAML catalog (was Object Repository/*.rs)
├── InputFiles/CRDC/        # PBAC Excel, MetadataData/TC08, DSV_ValidationResults-mappings.xlsx
├── config/                 # qa / qa2 / stage (was Profiles/*.glbl)
├── auth/                   # saved Login.gov cookies (gitignored)
├── reports/                # HTML + failure screenshots (gitignored)
└── docs/onboarding.md
```

| If you used this in Katalon | Look here instead |
|---|---|
| `Test Cases/CRDC/AuxiliaryTests/TC08_ManageStudiesListAndFilter` | `tests/AuxiliaryTests/test_TC08_ManageStudiesListAndFilter.py` |
| `Scripts/CRDC/.../Script….groovy` | `tests/<Area>/test_TC##_….py` |
| `WebUI.closeBrowser()` + `loginToCrdcOtp` at the top of every script | `tests/conftest.py` (`hub` fixture) |
| `CustomKeywords.'utilities.Login.loginToCrdcOtp'` | `src/crdc_pw/auth.py` (called by the fixture, not the test) |
| `findTestObject` + `WebUI.click` inside that Groovy | `src/crdc_pw/pages/` (`LoginPage`, `HeaderPage`, list pages) |
| `PythonFiles/CRDC/GenerateOtp.py` | `src/crdc_pw/utils/otp.py` |
| Data File `CRDC/Pbac/Permissions` | `InputFiles/CRDC/PBACPermissions.xlsx` + `utils/pbac_sheet.py` |
| Object Repository `CRDC/Login/...` | `locators/CRDC/**/*.yaml` + `LocatorLoader` |
| `Profiles/CRDC_QA.glbl` / `GlobalVariable` | `config/qa.yaml` |
| Test Suite `CRDC_Smoke.ts` | `pytest -m CRDC_Smoke` |
| Test Suite `CRDC_Auxiliary.ts` | `pytest -m CRDC_Auxiliary` |
| Test Suite `CRDC_PBAC.ts` | `pytest -m CRDC_PBAC` |
| Test Suite `CRDC_DataValidation.ts` | `pytest -m CRDC_DataValidation` |
| `Test Cases/CRDC/DataSubmissions/GC/CRDCDH-686-Partial/TC08_...` | `tests/DataSubmissions/GC/test_TC08_CRDC-VerifyInvalidIntegerValue.py` |

### Fixture, page, test (no keyword layer)

Katalon had **no separate page layer**. `Login.groovy` was both the journey (`loginToCrdcOtp`) and the clicks (`findTestObject`, `setText`, `click`). This repo splits that Groovy class into a **fixture** (session) and **page objects** (screens). There is no `keywords/` package.

| | **Fixture** (`hub`) | **Page** (`pages/`) | **Utils** (`utils/`) | **Test** (`tests/`) |
|---|---|---|---|---|
| Question it answers | Who is signed in, on which tab? | What can you do *on this screen*? | How does Hub compare to a file / GitHub / TOTP? | What is the scenario, and did it pass? |
| Example | Login.gov OTP, saved cookies, `hub.role` | `open()`, `apply_filters()`, `markdown_text()` | `write_expected` / `compare_actual`, `published_notes_snippet` | `expect(studies.container).to_be_visible()` |
| Uses | `auth.py` + `LoginPage` / `HeaderPage` | Locator properties → YAML → Playwright (15s `BasePage.DEFAULT_MS`) | Excel, HTTP GET, `pyotp` | Page objects + optional utils + `expect` / `assert` |
| Test calls it? | Asks for `hub` (already signed in). Uses `auth.switch_user(hub, role)` only when the *scenario* changes user | Yes — `StudiesListPage(hub.page, hub.locators)` | Yes, when the case needs an oracle (TC01, later 3979) | This *is* the test |

Adding a new list case (TC12) does not touch `Hub` or `conftest.py`. You write a page object and a pytest file.

### What `hub` is

`hub` is **not** the Hub website. It is a thin Python object pytest builds **before** your test function runs: **one Chromium tab, already on Hub, already signed in as a role**. Tests construct page objects from it. It has no `studies` / `programs` / `login` / `header` fields.

Katalon equivalent: the moment *after* `navigateToCrdc()` + `loginToCrdcOtp('Admin')`, browser still open. That whole situation is `hub`.

| You write | What it is |
|---|---|
| `hub.page` | The browser tab |
| `hub.role` | `'Admin'`, `'Fedlead'`, … |
| `hub.locators` | Loaded YAML (`LocatorLoader`) — pages use this |
| `hub.settings` | URL + credentials for this run |

If a test only asks for `hub`, the role is **Admin**. A case that needs every role (TC18) parametrizes `hub` with `indirect=True` so each role gets a **new** browser — like Katalon `closeBrowser` between users, except each role is its own pytest result.

### Walkthrough: TC08 Manage Studies

Command: `pytest -m CRDC_Auxiliary -k TC08`.

**The test file itself** (`tests/AuxiliaryTests/test_TC08_ManageStudiesListAndFilter.py`) assumes `hub` is already signed in as Admin. The file is the scenario: open the list, check chrome, filter, assert rows.

```python
def test_TC08_ManageStudiesListAndFilter(hub: Hub) -> None:
    studies = StudiesListPage(hub.page, hub.locators)
    studies.open()
    expect(studies.container).to_be_visible()
    expect(studies.add_study).to_be_visible()
    studies.apply_filters(study_name="autoQA", program="AutoTest-Program")
    assert studies.row_count() >= 1
    assert any("autoQA" in cell for row in studies.read_table_rows() for cell in row)
```

Login already happened. Read **down** this list to see the clicks.

**1. Once per pytest process** — `tests/conftest.py`

- `settings` = `config/qa.yaml` (or whatever `CRDC_PROFILE` is)
- `locators` = `LocatorLoader()` reads every file under `locators/CRDC/` into memory (`"CRDC/Login/Login.gov-Btn"` → XPath). Same job as opening Object Repository.

**2. The `hub` fixture** (session setup, not the scenario)

1. Role defaults to `"Admin"` (TC08 does not parametrize).
2. If `AdminEmail` / `AdminPassword` / `AdminSecret` are blank → skip, not fail.
3. `ensure_storage_state("Admin")` — file lock on `auth/qa/Admin.json`. If the json is missing or the Hub header is not that role, Login.gov OTP writes it (once per role per worker). Other workers wait on the lock instead of OTPing the same account.
4. New Chromium context from that json (new tab per test, not a shared page).
5. `land_on_hub` — goto Hub URL; wait until Continue **or** the username is visible; click Continue only if the banner is what appeared. No 3s header + 5s banner wait on every test.
6. **Now** pytest calls your test function with `Hub(...)`.
7. After the test: close the **current** context (`WebUI.closeBrowser()`). `switch_user` may have replaced the page; teardown closes whatever Hub is using. Failure screenshots go on the HTML report under `reports/`.

**3. Inside `login_otp` (only when cookies were dead)** — `src/crdc_pw/auth.py`

The fixture session is the **story**. It does not contain XPaths. It calls the login **page**:

- `start_login_gov()` — Hub Login button, then Login.gov icon
- `submit_credentials(email, password)` — from the yaml, not the test
- Wait for OTP **or** Grant **or** rare extra pages (Rules of Use, NIH agree)
- If OTP: `totp_now(secret)` from `utils/otp.py`, then `submit_otp(code)`
- If Grant: `click_grant()`
- Then `header.username()` to confirm Hub is up

**4. Inside a page click** — `src/crdc_pw/pages/`

`studies.open()` (the line the **test** calls) goes to `HeaderPage.open_manage_studies()`, then waits for the list container. Tests assert `studies.container`; the page maps that to YAML via `_loc()`:

```
studies.container
    → _loc("CRDC/AILocators/Studies/List/Container")
    → LocatorLoader.get(path)     # YAML → XPath
    → page.locator(xpath)         # Playwright, this tab
    → wait until visible (15s Hub default), then read or click
```

The test never sees the XPath or the Katalon path. If a locator is wrong, the failure is usually in a **page** wait, not in the filter asserts.

**5. Back in the test** — already logged in

| Line | What it is doing |
|---|---|
| `StudiesListPage(hub.page, hub.locators)` | Bind the Manage Studies screen to this tab |
| `studies.open()` | User menu → Manage Studies, wait for the list |
| `expect(studies.container)` / `studies.add_study` | List chrome is up |
| `studies.apply_filters(study_name="autoQA", program="AutoTest-Program")` | Same filter values as Katalon |
| `assert` row count / `"autoQA"` in a cell | Fail if the filtered table is empty or off |

The fixture is how we signed in. Tests do not call `login_otp` again. They call `auth.switch_user(hub, role)` only when the *scenario* changes user (PBAC).

```
pytest
  load qa.yaml + all YAML locators          (session)
  open tab (+ maybe auth/qa/Admin.json)
  fixture: auth.LoginSession signs in as Admin
  yield Hub                                 ← test starts here, already on Hub
      TEST: StudiesListPage + expect/assert
  close tab
```

### If something fails, where to look

| Symptom | Open this first |
|---|---|
| Skip: missing AdminEmail | `config/qa.yaml` |
| Never reaches Hub / OTP timeout | `auth.py` then `pages/login.py` |
| Timeout on a button name you recognize | YAML under `locators/CRDC/` for that Katalon path |
| Logged in but username assert fails | `pages/header.py` |
| Timeout on Manage Studies / filters | `pages/studies.py` then YAML under `locators/CRDC/AILocators/Studies/` |
| Timeout on Release Notes / empty markdown | `pages/release_notes.py` then YAML under `locators/CRDC/AILocators/ReleaseNotes/` and Footer |
| PBAC Pass/Fail in Excel | `utils/pbac_sheet.py` and `OutputFiles/PBAC_Defaults_Results.xlsx` |
| Timeout on Data Submissions create / Validate / VR table | `pages/data_submissions.py` then YAML under `locators/CRDC/DataSubmissions/` |
| VR vs expected TSV mismatch | `utils/validation_results.py` and `InputFiles/CRDC/MetadataData/<TC>/expected-ValidationResults/` |
| “Who even opened the browser?” | `tests/conftest.py` fixture `hub` |

### Other live cases (same pattern)

**TC09** is the Programs twin (`tests/AuxiliaryTests/test_TC09_ManageProgramsListAndFilter.py`): `ProgramsListPage(hub.page, hub.locators).open()`, then filters `AutoTest` / `autoQA`, then at least one row contains `auto`.

**TC18** only asserts that each role landed on Hub (header username, URL is Data Commons, not Login.gov). It parametrizes `hub` across the six roles; there is no list page after login.

**CRDCDH-3974** (`tests/AuxiliaryTests/test_TC_CRDCDH-3974_ReleaseNotesPage.py`): footer → `/release-notes`, markdown visible, error alert hidden, text non-empty. A GitHub static-content compare is sketched in `utils/static_content.py` but not called until CRDCDH-3979.

**TC01** (`tests/Pbac/test_TC01_CRDC-PbacDefaultPermissions-Fedlead.py`) is the **middle** of Katalon TC01 (not `loginToCrdcOtp` / `closeBrowser`). Fixture already signed in as Admin. The page reads checkboxes; `utils/pbac_sheet.py` owns the Excel compare — no `verify_*` on the page:

```python
def test_TC01_CRDC_PbacDefaultPermissions_Fedlead(hub: Hub) -> None:
    users = ManageUsersPage(hub.page, hub.locators)
    users.open()
    users.find_and_edit("Fedlead")
    users.reset_permissions("Fedlead")
    users.find_and_edit("Fedlead")
    users.expand_permission_panels()
    write_expected("Fedlead")
    assert compare_actual("Fedlead", users.read_permission_rows())

    switch_user(hub, "Fedlead")
    profile = UserProfilePage(hub.page, hub.locators)
    profile.open()
    profile.expand_permission_panels()
    write_expected("Fedlead-self")
    assert compare_actual("Fedlead-self", profile.read_permission_rows())
```

`navigate`, `closeBrowser`, viewport, and the first OTP stay in the fixture. Scenario clicks stay in the pytest file as page-object calls — not as raw XPaths.

**TC08 invalid integer** (`tests/DataSubmissions/GC/test_TC08_CRDC-VerifyInvalidIntegerValue.py`) is Submitter, not Admin. Marker `CRDC_DataValidation` so `pytest -m CRDC_Auxiliary -k TC08` still means Manage Studies only. Same steps as Katalon after login: create a New GC metadata-only DS, `upload_folder("TC08")`, `click_validate()`, then `verify_validation_results_vs_expected_for_tc("TC08", model="GC")`. Expected TSV matching is `utils/validation_results.py`. It leaves the `auto-test_*` submission (Katalon does too).

**Excel Data Validation** cases (commons-style `Steps` sheet, `TC*.xlsx` under `tests/DataValidation/`): collected when `excel_ds_validation.enabled` is true (default in profile examples). See [excel-ds-validation.md](excel-ds-validation.md). Run all: `pytest tests/DataValidation -m CRDC_DataValidation_Excel`; one case: add `-k TC08`. Python TC08 under `tests/DataSubmissions/GC/` stays collected in parallel.

---

## Environments (QA / QA2 / Stage)

One gitignored YAML file per Hub environment, same idea as a Katalon profile:

| File | Katalon profile | Hub |
|---|---|---|
| `config/qa.yaml` | `CRDC_QA` | https://hub-qa.datacommons.cancer.gov/ |
| `config/qa2.yaml` | `CRDC_QA2` | https://hub-qa2.datacommons.cancer.gov/ |
| `config/stage.yaml` | `CRDC_STAGE` | https://hub-stage.datacommons.cancer.gov/ |

Each file holds **`base_url` plus the six role accounts** (`AdminEmail` / `AdminPassword` / `AdminSecret`, and the same for Fedlead, Dcp, Submitter, User, Master). `*Secret` is the Login.gov TOTP seed, not the six-digit code.

Committed templates (URLs filled, secrets blank):

- `config/qa.yaml.example`
- `config/qa2.yaml.example`
- `config/stage.yaml.example`

**How the framework picks an environment:** the shell variable `CRDC_PROFILE`. Allowed values: `qa`, `qa2`, `stage`. If you do not set it, it defaults to **`qa`**.

```bash
# uses config/qa.yaml
pytest -m CRDC_Auxiliary

# uses config/qa2.yaml
CRDC_PROFILE=qa2 pytest -m CRDC_Auxiliary
```

Editing `qa2.yaml` does nothing unless `CRDC_PROFILE=qa2`. There is no pytest `--profile` flag yet.

Do **not** commit `config/qa.yaml` (or qa2/stage). They contain passwords and TOTP seeds.

---

## Setup (first time)

### 1. Prerequisites

- macOS or Linux
- **Python 3.11 or newer** (`python3 --version`)
- Git
- Access to the Hub automation accounts (ask the team for the Katalon profile values, or copy them from `crdc-dh-automation` `Profiles/CRDC_QA.glbl` on a machine that already has them)

Chromium is installed in step 3; you do not need to install Chrome separately.

### 2. Clone and enter the repo

```bash
cd crdc-dh-automation-pw
```

### 3. Virtualenv, package, browser

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

Stay in the venv for later commands (`which python` should point at `.venv`).

On Windows (PowerShell): `.venv\Scripts\Activate.ps1` instead of `source .venv/bin/activate`.

### 4. Credentials

```bash
cp config/qa.yaml.example config/qa.yaml
```

Open `config/qa.yaml` and fill Email / Password / Secret for every role you need. Copy from the matching Katalon profile (`CRDC_QA` for qa). Blank roles are **skipped**, not failed.

For QA2 or Stage:

```bash
cp config/qa2.yaml.example config/qa2.yaml
# fill, then:
CRDC_PROFILE=qa2 pytest -m CRDC_Auxiliary
```

### 5. Confirm unit tests (no Hub, no accounts)

```bash
pytest tests/unit -m unit
```

All of these should pass on a fresh clone, even before you fill `qa.yaml`.

Optional lint (not required to run tests, does not run on `git commit`): `pip install -e ".[dev]"` then `ruff check src tests` and `mypy src/crdc_pw`.

---

## Run tests

Always activate the venv first (`source .venv/bin/activate`).

| What | Command |
|---|---|
| Unit (no browser) | `pytest tests/unit -m unit` |
| Katalon Auxiliary suite | `pytest -m CRDC_Auxiliary` |
| Katalon Smoke subset (TC08, TC09 today) | `pytest -m CRDC_Smoke` |
| Same smoke, four workers (cookies warm) | `pytest -m CRDC_Smoke -n 4` |
| Katalon PBAC suite | `pytest -m CRDC_PBAC` |
| Same, watch the browser | `pytest -m CRDC_Auxiliary --headed` |
| TC18 one role | `pytest -m CRDC_Auxiliary -k Admin` |
| TC08 Manage Studies list only | `pytest -m CRDC_Auxiliary -k TC08` |
| TC09 Manage Programs list only | `pytest -m CRDC_Auxiliary -k TC09` |
| TC01 PBAC Fedlead defaults | `pytest -m CRDC_PBAC -k TC01` |
| Katalon Data Validation suite | `pytest -m CRDC_DataValidation` |
| TC08 invalid integer (GC metadata VR) | `pytest -m CRDC_DataValidation -k "VerifyInvalidInteger"` |
| **All Excel DS validation cases** | `pytest tests/DataValidation -m CRDC_DataValidation_Excel` |
| **One Excel case** (e.g. TC08) | `pytest tests/DataValidation -m CRDC_DataValidation_Excel -k TC08` |
| CRDCDH-3974 Release Notes | `pytest -m CRDC_Auxiliary -k 3974` |
| TC18 file only | `pytest tests/AuxiliaryTests/test_TC18_LoginAllRolesAndSwitchUser.py` |
| Against QA2 | `CRDC_PROFILE=qa2 pytest -m CRDC_Auxiliary` |

TC18 is Katalon **TC18_LoginAllRolesAndSwitchUser** (`CRDC_Auxiliary`, not `CRDC_Smoke`) at `tests/AuxiliaryTests/test_TC18_LoginAllRolesAndSwitchUser.py`. It checks that each role lands on Hub (username in the header, URL is Data Commons, not Login.gov). The `test_` prefix is required so pytest collects the file; the rest of the name matches Katalon.

Every run writes `reports/report-YYYYMMDD-HHMMSS.html` (gitignored, Katalon-style new file per run). Override with `--html=path`. A failed live test embeds a full-page screenshot in that HTML and writes a PNG under `reports/screenshots/`.

Useful pytest extras:

```bash
pytest -m CRDC_Auxiliary --headed --slowmo 300   # slow the UI down to watch
pytest -m CRDC_Smoke -n 4                            # parallel; lock serializes OTP per role
pytest tests/unit -m unit -q                         # quieter (leave -n off)
```

Failed live tests keep a Playwright trace of the **Hub tab** under `test-results/` (gitignored). OTP setup windows are not traced. Passing tests do not keep a zip unless you pass `--tracing=on`.

```bash
playwright show-trace test-results/**/trace.zip
```

The folder name matches the test file (for example `tests-auxiliarytests-test-tc08-...`). The viewer is local, not Hub: timeline, action list (the last wait is often the failure), before/after DOM snapshots, and network. TC01 (`switch_user`) can write `trace.zip` and `trace-2.zip`. Locally, `--headed` is usually enough to watch Login.gov.

---

## Saved sessions (`auth/`)

The first successful Login.gov login for a role writes cookies to:

```
auth/<profile>/<Role>.json
```

Example: `auth/qa/Admin.json`. That folder is gitignored.

The next run’s first worker for that role opens Hub and checks the header. If the Hub session (`connect.sid`) is still valid, OTP is skipped and later tests only load the json. If it expired, OTP runs once and overwrites the file. Tests do not re-check the header on every case.

If login looks “stuck” on an old user or a bad cookie:

```bash
rm -rf auth/qa
```

Then rerun smoke. You will pay OTP once per role again.

A **FileLock** on `auth/<profile>/<Role>.json.lock` serializes OTP for the same account, so `pytest -n 4` is safe. Different roles may OTP in parallel. Do not put `-n` in `pytest.ini` (first-time OTP and unit tests stay serial unless you pass `-n` yourself).

---

## Porting a Katalon case (later)

When you copy a case over:

- Keep the **TC name** in the module docstring or test name so Xray / ticket mapping still works
- Port the **steps and assertions**, not `WebUI.delay`, JS clicks, or stale-element retries
- Put new locators in YAML under `locators/CRDC/`, not as XPath strings in the test
- Put Hub actions in `pages/`. The pytest file is the Katalon script **after** login: scenario + asserts, not Selenium
- Do not open the browser or call `login_otp` in the test; ask for `hub` (already signed in). Use `auth.switch_user(hub, role)` only when the scenario changes role
- Do not close the browser in the test; the fixture does that

---

## GitHub Actions (CI)

CI is **GitHub Actions**, not Jenkins. The workflow is still `workflow_dispatch` only (not on every PR yet). Default integration branch is **`develop`**.

Because `qa.yaml` is gitignored, a checkout does **not** contain passwords.

- **Unit job:** uses `*.yaml.example` (URLs only). No secrets needed.
- **Smoke job (later):** GitHub Environments named `qa` / `qa2` / `stage` hold the same Katalon secret names. A step runs `python ci/write_profile_yaml.py` to write `config/<profile>.yaml` on the runner, then pytest runs as usual.

Details: [ci/README.md](../ci/README.md).

---

## Troubleshooting

| What you see | Likely cause | What to do |
|---|---|---|
| `SKIPPED` … Missing AdminEmail | `config/qa.yaml` missing or blank | Copy the example and fill secrets |
| Tests hit QA2 by accident | `CRDC_PROFILE` still set in the shell | `echo $CRDC_PROFILE`; unset it or set `qa` |
| Timeout on OTP / Grant | Login.gov or Hub slow; OTP window | Rerun; Grant can take 30s+. Do not start a second login for the same user |
| Username empty / still on login.gov | Session expired or login failed | `rm auth/<profile>/<Role>.json` and rerun `--headed` |
| `Profile config not found` | Typo in `CRDC_PROFILE` | Must be exactly `qa`, `qa2`, or `stage` |
| Unit tests fail on locators | Incomplete clone | `locators/CRDC/` must be present |
| `playwright` / browser missing | Step 3 skipped | `pip install -e .` then `playwright install chromium` |
| Wrong Python | venv not active | `source .venv/bin/activate` |

---

## What not to commit

- `config/qa.yaml`, `qa2.yaml`, `stage.yaml`
- `.env` (leftover; this project does not use it anymore)
- `auth/**` session JSON
- `.venv/`

The `*.yaml.example` files **are** committed (no secrets).

---

## Where to look next

| Topic | Place |
|---|---|
| This onboarding | `docs/onboarding.md` |
| Short project README | `README.md` |
| CI / GitHub secrets | `ci/README.md` |
| Migration plan (phases, what to port vs drop) | `ai/crdc/Playwright-Migration-Plan.md` in the sibling `ai` tree |
| Katalon source of truth (until cutover) | `crdc-dh-automation` |
| Object repository YAML | `locators/CRDC/` |

Questions about accounts or which environment to use for a given ticket: ask the QA lead before pointing tests at Stage.
