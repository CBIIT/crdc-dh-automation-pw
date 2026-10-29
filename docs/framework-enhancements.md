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
| Rejected | Reviewed; will not do |

---

## Ranked work (scale)

### 1. Auth once per role, then parallel — Open

**Problem:** Every live test opens a context, hits Hub, waits up to 3s for the header and 5s for the banner. That is 5–10s of overhead even with a valid cookie. At 300 tests that is 25–50 minutes before any scenario runs. There is no lock on `auth/<profile>/<role>.json`, so `pytest -n 8` races OTP for the same account (onboarding already says never do that).

**Target:** One auth setup per role per session, file-locked, before workers start. Tests load `storage_state` and go to the target URL without re-checking the header. Playwright TypeScript “setup project” is the reference. Then enable xdist. Measure wall time before and after.

**Where:** `tests/conftest.py`, `src/crdc_pw/auth.py`, later CI.

**Plan (not implemented):** [auth-once-then-parallel.md](auth-once-then-parallel.md).

### 2. Playwright waits, one timeout policy — Done

**Problem:** Pages use Selenium-style `wait_for(..., timeout=N)` plus `try/except` returning a bool. Many hand-tuned timeouts (1s–30s). Swallowed timeouts (`pass`) push the real failure downstream. Optional checks that are absent pay the full timeout.

**Race already in tree:** `wait_for_table_settled` in `pages/studies.py` waits for the loading row to be hidden. If the filter is debounced and the spinner has not appeared yet, the wait returns immediately and the next read sees stale rows. Wait on network or on table content changing instead.

**Target:** Prefer `expect(locator).to_be_visible()` with one project-wide timeout. Use `locator.or_()` for either-or states (`pages/release_notes.py` already does this). Remove swallowed timeouts.

**Where:** `BasePage` (`DEFAULT_MS` 15s on context + expect, `PROBE_MS` 2s for optional chrome, `RELEASE_NOTES_MS` 30s for the GitHub fetch). Table wait on `BasePage._wait_for_table_settled`. Login.gov timings stay in `login.py` / `auth.py`.

### 3. YAML XPath as destination — Deferred

Katalon paths and `page.locator(xpath)` are a **transition** layer, not the end state. Semantic locators (`get_by_test_id`, `get_by_role`), strict mode, and retiring `.first` / duplicate YAML trees (`CRDC/Login` vs `CRDC/AILocators/Login`, identical XPaths under different names) stay **out of this backlog** until we explicitly start retiring YAML.

Keep using YAML for dual-run. Do not block remaining Open items on this.

### 4. Locator properties on pages — Done

**Problem:** Tests import path constants and write `expect(studies.loc(CONTAINER))`. That leaks the lookup mechanism into every case.

**Target:** Locators as properties on the page: `expect(studies.container).to_be_visible()`. The page is the only place that knows the Katalon path (or, later, a semantic locator).

**Where:** `pages/*.py` (`_loc` + named properties), TC08 / TC09 / CRDCDH-3974. YAML stays (#3 deferred). Tests use `expect(studies.container)`, not `loc(CONTAINER)`.

### 5. Shared UI kit before more pages — Done

**Problem:** `_is_visible`, `_fill_if_visible`, `_select_dropdown`, `wait_for_table_settled`, `read_table_rows`, `_trim` are copied across `studies.py`, `programs.py`, and `users.py`. Fine at three pages. Painful at thirty.

**Target:** Shared widget helpers on `BasePage` (not a `components/` package and not `utils/`). Pages still own YAML paths and `apply_filters`. Do this **before** SR and DS.

**Where:** `BasePage._trim`, `_select_dropdown(dropdown, option)`, `_read_table_rows(rows)`, `_wait_for_snackbar_gone(snackbar)` (PROBE then hidden). Table wait was already on `BasePage` (#2). Pagination stays on `users.py` until a second list page needs it. No `FilterBar` class.

### 6. PBAC oracle: label match, scoped locators, per-run output — Rejected

**Problem:** `compare_actual` in `utils/pbac_sheet.py` matches sheet row *i* to UI checkbox *i*. A new permission anywhere shifts every row. Checkbox xpath `//input[@type='checkbox']` is page-global. Shared `OutputFiles/PBAC_Defaults_Results.xlsx` will collide under parallel runs.

**Target (not taking):** Match on label. Scope checkboxes to the two accordions. Per-run output instead of one mutated workbook.

**Why not:** Positional compare is Katalon-shaped and working. A new permission in the middle of the form already fails loudly; QA adds the row to `PBACPermissions.xlsx`. Display names repeat (`View`), so label match can pair the wrong checkbox and Pass. Do not rewrite `compare_actual`. Scoped locators and a unique output path are optional later (parallel PBAC), not a reason to change pairing.

---

## Smaller items (fix while the tree is small)

| Item | Problem | Target | Status |
|---|---|---|---|
| Tooling | `dev = []`, no ruff/mypy/lockfile/pre-commit | `pip install -e ".[dev]"` for ruff and mypy. No lockfile, no `requirements.txt`, no pre-commit (git commit unchanged). | Done |
| Tracing | Screenshot only (Katalon-shaped) | `--tracing=retain-on-failure` in addopts. Open a fail with `playwright show-trace test-results/.../trace.zip`. | Done |
| Markers | Every live test is `smoke`, including PBAC reset | Katalon suite names (`CRDC_Auxiliary`, `CRDC_PBAC`, `CRDC_Smoke`, …). `--strict-markers`. Only Katalon smoke members get `CRDC_Smoke`. | Done |
| Test logging | `log.info("Assert ...")` / `log.info("PASS TC08 ...")` will be copied 300 times | Leave as-is. Assert/PASS lines and `log_cli = true` are how QA follows live runs (Katalon logInfo). Sweeping tests would not catch a defect. | Rejected |
| Locator contract test | Typo in a `CRDC/...` string fails after a 15s live timeout | Unit test: every `CRDC/` string in `pages/` exists in the loader. | Done |
| Hardcoded conventions | `pbac.{role}-automation` in `auth.py`; `datacommons.cancer.gov` in TC18; `autoQA` / `AutoTest-Program` in tests | Leave as-is. Those are the real Hub account and filter names. TC18 already uses `settings.base_url`. Do not add a config scheme. | Rejected |
| `switch_user` | Reuses a context after clearing cookies | Leave as-is. `switch_user` already exists (TC01 Admin → Fedlead). Same-tab logout + cookie clear works. Do not rewrite auth unless it flakes. | Rejected |
| Loader dual API | Attribute access (`locators.CRDC...`) is unused, extra duplicate rules | Keep `get(path)` only. | Done |
| Bare `except Exception` | `HeaderPage.is_logged_in` treats a closed/crashed page as “not logged in” and may trigger OTP | Catch the specific timeout / closed-page errors only. | Done |
| Filter warnings | `filterwarnings = ignore::DeprecationWarning` | Stop hiding Playwright upgrade signals. | Done |

---

## Suggested order

Do these in this sequence unless a live flake forces a jump (e.g. banner timeout).

1. **Auth setup once per role with a lock, then xdist.** Measure before and after.

Locator properties (#4), Hub wait policy (#2), shared UI helpers (#5), traces, loader `get()`-only, and ruff/mypy (`dev` extra) are done. PBAC oracle (#6), test logging, hardcoded names, and a `switch_user` rewrite are rejected. Strict mode and retiring `.first` wait until YAML retirement (#3) is in scope.

## Out of scope here

- Retiring YAML / moving to `get_by_test_id` (#3).
- Porting SR, DS, email, Mongo (see onboarding planned order).
- Changing the fixture / page / test split.
