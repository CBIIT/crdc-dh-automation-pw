# Framework enhancements

Backlog from an external review of `crdc-dh-automation-pw` (Oct 2026), while the suite is still small (login smoke, TC08, TC09, TC01, CRDCDH-3974). The architecture is not the risk. Per-test login cost and copy-pasted pages are fine at five tests and painful at fifty.

Do this work **before** Submission Requests and Data Submissions land, not after a two-hour run forces it.

Human walkthrough of how the framework works today: [onboarding.md](onboarding.md).

## What to keep

- **Layers:** fixture builds a signed-in session; tests own the scenario and asserts; pages act and read; locators live in YAML. “Pages read, tests decide” stays.
- **Login:** OTP, Grant, Rules of Use, NIH agree, SSO reuse, protected-page modal, `storage_state`, skip-not-fail on blank credentials.
- **Hygiene:** gitignored secrets, per-env config, unit tests for non-browser logic, failure screenshots on the HTML report.

## Status key

| Status | Meaning |
|---|---|
| Open | Do this; not started |
| Deferred | Leave until dual-run / YAML retirement is an explicit project |
| Done | Shipped |

---

## Ranked work (scale)

### 1. Auth once per role, then parallel — Open

**Problem:** Every live test opens a context, hits Hub, waits up to 3s for the header and 5s for the banner. That is 5–10s of overhead even with a valid cookie. At 300 tests that is 25–50 minutes before any scenario runs. There is no lock on `auth/<profile>/<role>.json`, so `pytest -n 8` races OTP for the same account (onboarding already says never do that).

**Target:** One auth setup per role per session, file-locked, before workers start. Tests load `storage_state` and go to the target URL without re-checking the header. Playwright TypeScript “setup project” is the reference. Then enable xdist. Measure wall time before and after.

**Where:** `tests/conftest.py`, `src/crdc_pw/auth.py`, later CI.

**Plan (not implemented):** [auth-once-then-parallel.md](auth-once-then-parallel.md).

### 2. Playwright waits, one timeout policy — Open

**Problem:** Pages use Selenium-style `wait_for(..., timeout=N)` plus `try/except` returning a bool. Many hand-tuned timeouts (1s–30s). Swallowed timeouts (`pass`) push the real failure downstream. Optional checks that are absent pay the full timeout.

**Race already in tree:** `wait_for_table_settled` in `pages/studies.py` waits for the loading row to be hidden. If the filter is debounced and the spinner has not appeared yet, the wait returns immediately and the next read sees stale rows. Wait on network or on table content changing instead.

**Target:** Prefer `expect(locator).to_be_visible()` with one project-wide timeout. Use `locator.or_()` for either-or states (`pages/release_notes.py` already does this). Remove swallowed timeouts.

**Where:** `pages/*.py`, `pytest.ini` / Playwright default timeout.

### 3. YAML XPath as destination — Deferred

Katalon paths and `page.locator(xpath)` are a **transition** layer, not the end state. Semantic locators (`get_by_test_id`, `get_by_role`), strict mode, and retiring `.first` / duplicate YAML trees (`CRDC/Login` vs `CRDC/AILocators/Login`, identical XPaths under different names) stay **out of this backlog** until we explicitly start retiring YAML.

Keep using YAML for dual-run. Do not block items 1, 2, 4–6 on this.

### 4. Locator properties on pages — Done

**Problem:** Tests import path constants and write `expect(studies.loc(CONTAINER))`. That leaks the lookup mechanism into every case.

**Target:** Locators as properties on the page: `expect(studies.container).to_be_visible()`. The page is the only place that knows the Katalon path (or, later, a semantic locator).

**Where:** `pages/*.py` (`_loc` + named properties), TC08 / TC09 / CRDCDH-3974. YAML stays (#3 deferred). Tests use `expect(studies.container)`, not `loc(CONTAINER)`.

### 5. Shared UI kit before more pages — Open

**Problem:** `_is_visible`, `_fill_if_visible`, `_select_dropdown`, `wait_for_table_settled`, `read_table_rows`, `_trim` are copied across `studies.py`, `programs.py`, and `users.py`. Fine at three pages. Painful at thirty.

**Target:** Components pages compose: `GenericTable`, `MuiSelect`, `FilterBar`, `Snackbar`. Do this **before** SR and DS, not after (onboarding already lists this as planned step 2).

**Where:** new `src/crdc_pw/components/` (or similar); then fold list pages onto it.

### 6. PBAC oracle: label match, scoped locators, per-run output — Open

**Problem:** `compare_actual` in `utils/pbac_sheet.py` matches sheet row *i* to UI checkbox *i*. A new permission anywhere shifts every row. Checkbox xpath `//input[@type='checkbox']` is page-global. Shared `OutputFiles/PBAC_Defaults_Results.xlsx` will collide under parallel runs.

**Target:** Match on label (both sides have it). Scope checkboxes to the two accordions. Per-run output (or assert in memory and attach the sheet), not one mutated workbook.

**Where:** `utils/pbac_sheet.py`, `locators/.../ManageUsers.yaml`, `pages/users.py`.

---

## Smaller items (fix while the tree is small)

| Item | Problem | Target | Status |
|---|---|---|---|
| Tooling | `dev = []`, no ruff/mypy/lockfile/pre-commit | Add ruff, mypy, pinned lock, pre-commit. Unchecked type hints drift. | Open |
| Tracing | Screenshot only (Katalon-shaped) | `--tracing=retain-on-failure` in addopts or CI. Trace viewer is the debugging upgrade. | Open |
| Markers | Every live test is `smoke`, including PBAC reset | Markers: `smoke`, `regression`, `area`, `slow`, `destructive`. `--strict-markers`. TC01 is not smoke. | Open |
| Test logging | `log.info("Assert ...")` / `log.info("PASS TC08 ...")` will be copied 300 times | Put context in assertion messages. Drop PASS lines. Revisit `log_cli = true` (noisy by default). | Open |
| Locator contract test | Typo in a `CRDC/...` string fails after a 15s live timeout | Unit test: every `CRDC/` string in `pages/` exists in the loader. | Open |
| Hardcoded conventions | `pbac.{role}-automation` in `auth.py`; `datacommons.cancer.gov` in TC18; `autoQA` / `AutoTest-Program` in tests | Username scheme configurable; TC18 host from `settings.base_url`; filter data per env (QA2/Stage may differ). | Open |
| `switch_user` | Reuses a context after clearing cookies | Fresh context (Katalon closed the browser). Save the new role’s `storage_state`. | Open |
| Loader dual API | Attribute access (`locators.CRDC...`) is unused, extra duplicate rules | Keep `get(path)` only. | Open |
| Bare `except Exception` | `HeaderPage.is_logged_in` treats a closed/crashed page as “not logged in” and may trigger OTP | Catch the specific timeout / closed-page errors only. | Open |
| Filter warnings | `filterwarnings = ignore::DeprecationWarning` | Stop hiding Playwright upgrade signals. | Open |

---

## Suggested order

Do these in this sequence unless a live flake forces a jump (e.g. PBAC positional match, banner timeout).

1. **Auth setup once per role with a lock, then xdist.** Measure before and after.
2. **Shared component layer and a single timeout policy.** Remove swallowed timeouts.
3. **Label-based PBAC comparison and scoped checkbox locator.** Per-run output before parallel PBAC.
4. **Tooling:** ruff, mypy, lockfile, tracing, markers, locator contract test.

Locator properties (#4) are done. Strict mode and retiring `.first` wait until YAML retirement (#3) is in scope.

Then the smaller table, cheapest first (bare except, filterwarnings, loader API, TC18 host, logging) unless they land naturally with 1–4.

## Out of scope here

- Retiring YAML / moving to `get_by_test_id` (#3).
- Porting SR, DS, email, Mongo (see onboarding planned order).
- Changing the fixture / page / test split.
