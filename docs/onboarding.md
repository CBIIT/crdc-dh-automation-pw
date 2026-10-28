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

### Today (Phase 0 — scaffold)

The framework can:

- Load Hub URL and Login.gov credentials from one YAML file per environment
- Look up locators the same way Katalon did (`CRDC/Login/...`)
- Sign in through Login.gov with TOTP (one-time password)
- Reuse a saved browser session so the next run does not pay OTP every time
- Smoke-test that **Admin, Fedlead, Dcp, Submitter, User, and Master** land on Hub

That is the floor everything else builds on. PBAC, Submission Requests, Data Submissions, emails, Mongo, and GraphQL are **not** here yet.

### End goal (after the port)

Replace the Katalon Hub suites with this repo so QA and CI run Playwright instead of Katalon:

| Area (Katalon today) | Rough size | Lands in this repo as |
|---|---:|---|
| Data Submissions | ~79 cases | `tests/` + DS keywords (largest slice) |
| Notification emails | ~27 | UI in Playwright; existing Gmail Python stays |
| Submission Requests | ~19 | SR form + list |
| PBAC | ~19 | First real suite after login |
| Admin / lists / aux | ~16 | Programs, Studies, institutions, dashboard |
| API | ~3 | GraphQL via HTTP, not the browser |

**Cutover rule:** dual-run a suite on QA until it matches Katalon, then retire that Katalon suite. Not a big-bang switch.

Planned order after this scaffold:

1. **PBAC defaults** (TC01–05) plus a couple of isolated PBAC tickets — first real functional tests
2. **Shared UI kit** — tables, filters, MUI dropdowns, snackbars (unblocks every list page)
3. **Submission Requests**
4. **Data Submissions** (upload, validate, results tables)
5. **Non-browser oracles** — Mongo, GraphQL, CLI uploader, Gmail
6. **Notifications and remaining admin**
7. **CI on GitHub Actions** for smoke + suites; Katalon retired suite by suite

If you are joining during the port, expect new tests to show up as pytest files that still mention the Katalon case name in a comment.

---

## How the framework is laid out

Every live Hub test uses the same pattern:

1. **Fixture** (`app`) — open the browser, sign in as a role (Login.gov / saved cookies). Same idea as Katalon `closeBrowser` + `loginToCrdcOtp` at the top of every script, except it is not copied into each pytest file.
2. **Test** — the *scenario*: navigate, click, assert. That is the middle of the Katalon Groovy, the part you used to read to understand the case.
3. **Keywords / pages** — how those scenario lines are implemented (XPaths stay in YAML).

Initial login is **setup**, not a line in the test. TC18 looks like “only asserts” because its scenario *is* “we are on Hub as this role.” PBAC and DS tests will show more lines (`open_manage_users`, `verify_permission_defaults`) after the same logged-in `app`.

If login or the browser fails, follow the plumbing table below. If you want to know *what the case is testing*, read the pytest file.

### Folders

```
crdc-dh-automation-pw/
├── tests/                  # pytest files (Katalon Test Case / Script)
│   ├── conftest.py         # builds `app`: browser + login  ← start here if login fails
│   ├── AuxiliaryTests/     # Katalon AuxiliaryTests (no extra CRDC/ — this repo is Hub only)
│   └── unit/               # no browser (locator + config checks)
├── src/crdc_pw/
│   ├── app.py              # the `App` toolbox the test receives
│   ├── keywords/           # user journeys (Login today; later Pbac, DS)
│   ├── pages/              # one screen: click / fill / read
│   ├── locators/loader.py  # Katalon path → XPath string
│   ├── config.py           # which yaml file, which role credentials
│   └── otp.py              # TOTP codes (was GenerateOtp.py)
├── locators/CRDC/          # YAML catalog (was Object Repository/*.rs)
├── config/                 # qa / qa2 / stage (was Profiles/*.glbl)
├── auth/                   # saved Login.gov cookies (gitignored)
└── docs/onboarding.md
```

| If you used this in Katalon | Look here instead |
|---|---|
| `Test Cases/CRDC/AuxiliaryTests/TC18_LoginAllRolesAndSwitchUser` | `tests/AuxiliaryTests/test_TC18_LoginAllRolesAndSwitchUser.py` |
| `Scripts/CRDC/.../Script….groovy` | `tests/<Area>/test_TC##_….py` |
| `WebUI.closeBrowser()` + `loginToCrdcOtp` at the top of every script | `tests/conftest.py` (`app` fixture) |
| `CustomKeywords.'utilities.Login.loginToCrdcOtp'` | `src/crdc_pw/keywords/login.py` |
| `findTestObject` + `WebUI.click` inside that Groovy | `src/crdc_pw/pages/` (`LoginPage`, `HeaderPage`) |
| Object Repository `CRDC/Login/...` | `locators/CRDC/**/*.yaml` + `LocatorLoader` |
| `Profiles/CRDC_QA.glbl` / `GlobalVariable` | `config/qa.yaml` |
| Test Suite `CRDC_Smoke.ts` | `pytest -m smoke` |

### Keywords vs pages (Katalon mixed these)

Katalon had **no separate page layer**. `Login.groovy` was both the journey (`loginToCrdcOtp`) and the clicks (`findTestObject`, `setText`, `click`). This repo splits that one Groovy class:

| | **Keyword** (`keywords/`) | **Page** (`pages/`) |
|---|---|---|
| Question it answers | What can the *user / test* do? | What can you do *on this screen*? |
| Example | `login_otp` (fixture); later `verify_permission_defaults` (test) | `click_grant()`, `fill` email, read username |
| Uses | One or more pages + yaml credentials + OTP | YAML path → Playwright locator |
| Test calls it? | Scenario steps (`app.pbac.…`, `app.login.switch_user`). Not the first login | Yes, for one screen (`app.header.username()`) |

You could put every method on a page. Keywords exist so `PbacKeywords` does not become another 1,600-line file that also owns every Manage Users button.

### What `app` is

`app` is **not** the Hub website. It is a Python object pytest builds **before** your test function runs: **one Chromium tab, already on Hub, already signed in as a role**, plus named helpers for that tab.

Katalon equivalent: the moment *after* `navigateToCrdc()` + `loginToCrdcOtp('Admin')`, browser still open. That whole situation is `app`.

| You write | What it is |
|---|---|
| `app.page` | The browser tab |
| `app.role` | `'Admin'`, `'Fedlead'`, … |
| `app.header` | Hub header page (`HeaderPage`) |
| `app.login` | Login.gov keyword (`LoginKeywords`) |
| `app.locators` | Loaded YAML (`LocatorLoader`) — pages use this, tests rarely do |
| `app.config` | URL + credentials for this run |

If a test only asks for `app`, the role is **Admin**. Smoke parametrizes `app` so each role gets a **new** browser — like Katalon `closeBrowser` between users, except each role is its own pytest result.

### Walkthrough: the smoke test (one role)

Command: `pytest -m smoke`. Pytest runs `test_TC18_LoginAllRolesAndSwitchUser` **six times** (Admin, Fedlead, Dcp, Submitter, User, Master). Follow **Admin** only.

**The test file itself** (`tests/AuxiliaryTests/test_TC18_LoginAllRolesAndSwitchUser.py`) assumes `app` is already signed in. For this case that *is* the scenario, so the file is three checks:

```python
def test_TC18_LoginAllRolesAndSwitchUser(app: App) -> None:
    username = app.header.username(timeout_ms=5000)
    assert username
    assert "datacommons.cancer.gov" in app.page.url
    assert "login.gov" not in app.page.url.lower()
```

Everything else already happened. Read **down** this list to see the clicks.

**1. Once per pytest process** (not per role) — `tests/conftest.py`

- `settings` = `config/qa.yaml` (or whatever `CRDC_PROFILE` is)
- `locators` = `LocatorLoader()` reads every file under `locators/CRDC/` into memory (`"CRDC/Login/Login.gov-Btn"` → XPath). Same job as opening Object Repository.

**2. Once per role — still `conftest.py`, the `app` fixture** (session setup, not the scenario)

1. Role string is `"Admin"` (from parametrize).
2. If `AdminEmail` / `AdminPassword` / `AdminSecret` are blank → skip, not fail.
3. Open a Chromium tab. If `auth/qa/Admin.json` exists, load those cookies (last successful Login.gov).
4. Build the keyword: `LoginKeywords(page, locators, settings)`. That keyword builds `LoginPage` and `HeaderPage` on the **same** tab.
5. `login.navigate()` → `LoginPage` goes to Hub URL, dismisses the system-use banner if it is there.
6. `login.is_logged_in()` → `HeaderPage` looks for the username button.
   - Visible → cookies still good; skip Login.gov.
   - Not visible → `login.login_otp("Admin")` (Katalon `loginToCrdcOtp`), then save `auth/qa/Admin.json`.
7. **Now** pytest calls your test function with `App(...)`.
8. After the test: close the tab (`WebUI.closeBrowser()`). Next role starts at step 2.

**3. Inside `login_otp` (only when cookies were dead)** — `src/crdc_pw/keywords/login.py`

The keyword is the **story**. It does not contain XPaths. It calls the login **page**:

- `start_login_gov()` — Hub Login button, then Login.gov icon
- `submit_credentials(email, password)` — from the yaml, not the test
- Wait for OTP **or** Grant **or** rare extra pages (Rules of Use, NIH agree)
- If OTP: `totp_now(secret)` then `submit_otp(code)`
- If Grant: `click_grant()`
- Then `header.username()` to confirm Hub is up

**4. Inside a page click** — `src/crdc_pw/pages/`

`HeaderPage.username()` (the line the **test** calls) and `LoginPage.click_grant()` (the line the **keyword** calls) both go through `BasePage.loc()`:

```
path string  e.g. CRDC/AILocators/Global/Header/Desktop/UserName-Btn
    → LocatorLoader.get(path)     # YAML → XPath
    → page.locator(xpath)         # Playwright, this tab
    → wait until visible, then read or click
```

The test never sees the XPath. If a locator is wrong, the failure is usually in a **page** wait, not in the three asserts.

**5. Back in the test** — already logged in

| Line | What it is doing |
|---|---|
| `app.header.username(5000)` | Read the Hub header name (page, not keyword) |
| `app.page.url` | Playwright URL of that same tab |
| `assert ...` | Fail **this role** if the name is empty or we are still on login.gov |

`app.login` is how the fixture signed in. Tests do not call `login_otp` again. They call `app.login.switch_user(...)` only when the *scenario* changes user (PBAC), or `app.pbac.…` for domain steps.

```
pytest
  load qa.yaml + all YAML locators          (session)
  per role:
      open tab (+ maybe auth/qa/Admin.json)
      fixture: LoginKeywords signs in
      yield App                             ← test starts here, already on Hub
          TEST: scenario + asserts
      close tab
```

### If something fails, where to look

| Symptom | Open this first |
|---|---|
| Skip: missing AdminEmail | `config/qa.yaml` |
| Never reaches Hub / OTP timeout | `keywords/login.py` then `pages/login.py` |
| Timeout on a button name you recognize | YAML under `locators/CRDC/` for that Katalon path |
| Logged in but username assert fails | `pages/header.py` |
| “Who even opened the browser?” | `tests/conftest.py` fixture `app` |

### Later tests (same pattern, more scenario lines)

TC18 is a thin scenario. **TC08** is the first case with visible scenario lines (`tests/AuxiliaryTests/test_TC08_ManageStudiesListAndFilter.py`):

```python
def test_TC08_ManageStudiesListAndFilter(app: App) -> None:
    app.studies.navigate_to_manage_studies()
    app.studies.verify_list_page()
    app.studies.apply_filters(study_name="autoQA", program="AutoTest-Program")
    app.studies.verify_filter_results(expect_at_least_rows=1, row_contains="autoQA")
```

Fixture already signed in as Admin. Filter values match Katalon (`autoQA` / `AutoTest-Program`).

**TC09** is the Programs twin (`tests/AuxiliaryTests/test_TC09_ManageProgramsListAndFilter.py`): `app.programs.navigate_to_manage_programs()`, then filters `AutoTest` / `autoQA`, then at least one row contains `auto`.

A ported PBAC case still uses the same logged-in `app`; the pytest file is the **middle** of Katalon TC01 (not `loginToCrdcOtp` / `closeBrowser`). Katalon today:

```groovy
CustomKeywords.'utilities.SubmissionRequest.loginToCrdcOtp'('Admin')
CustomKeywords.'utilities.WebUIUtils.clickTab'('CRDC/NavBar/ManageUsers-Btn')
CustomKeywords.'utilities.Pbac.verifyPbacPermissionDefaults'('Fedlead')
```

Same case here (shape only; `app.pbac` is not written yet). Fixture already signed in as Admin; **Manage Users and PBAC stay in the test**:

```python
def test_pbac_default_permissions_fedlead(app: App) -> None:
    # fixture already logged in as Admin
    app.header.open_manage_users()
    app.pbac.verify_permission_defaults("Fedlead")

    app.login.switch_user("Fedlead")
    app.header.open_profile()
    app.pbac.verify_permission_defaults("Fedlead-self")
```

`navigate`, `closeBrowser`, viewport, and the first OTP stay in the fixture. Scenario clicks stay in the pytest file as keyword/page calls — not as raw XPaths.

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
pytest -m smoke

# uses config/qa2.yaml
CRDC_PROFILE=qa2 pytest -m smoke
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
CRDC_PROFILE=qa2 pytest -m smoke
```

### 5. Confirm unit tests (no Hub, no accounts)

```bash
pytest tests/unit -m unit
```

All of these should pass on a fresh clone, even before you fill `qa.yaml`.

---

## Run tests

Always activate the venv first (`source .venv/bin/activate`).

| What | Command |
|---|---|
| Unit (no browser) | `pytest tests/unit -m unit` |
| Login smoke, all six roles (TC18) | `pytest -m smoke` |
| Same, watch the browser | `pytest -m smoke --headed` |
| One role | `pytest -m smoke -k Admin` |
| TC08 Manage Studies list only | `pytest -m smoke -k TC08` |
| TC09 Manage Programs list only | `pytest -m smoke -k TC09` |
| TC18 file only | `pytest tests/AuxiliaryTests/test_TC18_LoginAllRolesAndSwitchUser.py` |
| Against QA2 | `CRDC_PROFILE=qa2 pytest -m smoke` |

The login smoke is Katalon **TC18_LoginAllRolesAndSwitchUser** at `tests/AuxiliaryTests/test_TC18_LoginAllRolesAndSwitchUser.py`. It checks that each role lands on Hub (username in the header, URL is Data Commons, not Login.gov). The `test_` prefix is required so pytest collects the file; the rest of the name matches Katalon.

Useful pytest extras:

```bash
pytest -m smoke --headed --slowmo 300   # slow the UI down to watch
pytest tests/unit -m unit -q                         # quieter
```

On failure, Playwright can keep a trace (`--tracing=retain-on-failure` once that is wired in CI). Locally, `--headed` is usually enough to see Login.gov.

---

## Saved sessions (`auth/`)

The first successful Login.gov login for a role writes cookies to:

```
auth/<profile>/<Role>.json
```

Example: `auth/qa/Admin.json`. That folder is gitignored.

The next run loads that file, opens Hub, and checks that the header username is visible. If the Hub session (`connect.sid`) is still valid, OTP is skipped. If it expired, the fixture logs in again and overwrites the file.

If login looks “stuck” on an old user or a bad cookie:

```bash
rm -rf auth/qa
```

Then rerun smoke. You will pay OTP once per role again.

**Do not run two OTP logins for the same account at the same time.** TOTP codes are valid for ~30 seconds; two browsers sharing one secret will collide. Login is meant to be once per role, then reuse `storage_state`.

---

## Porting a Katalon case (later)

When you copy a case over:

- Keep the **TC name** in the module docstring or test name so Xray / ticket mapping still works
- Port the **steps and assertions**, not `WebUI.delay`, JS clicks, or stale-element retries
- Put new locators in YAML under `locators/CRDC/`, not as XPath strings in the test
- Put Hub actions in `keywords/` and `pages/`. The pytest file is the Katalon script **after** login: scenario + asserts, not Selenium
- Do not open the browser or call `login_otp` in the test; ask for `app` (already signed in). Use `app.login.switch_user` only when the scenario changes role
- Do not close the browser in the test; the fixture does that

---

## GitHub Actions (CI)

CI is **GitHub Actions**, not Jenkins. The workflow is a placeholder until this repo is on GitHub.

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
