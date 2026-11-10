# PBAC negative (unchecked) port plan — TC11–TC15

Goal: Playwright **`verify_permissions_functional(..., "negative")`** matches Katalon **`Pbac.verifyPermissionsFunctional(role, "negative")`**, so unchecked permissions are proven **not** accessible for each PBAC automation role.

**Source of truth:** Katalon `Test Cases/CRDC/Pbac/TC11`–`TC15` (`*UncheckedPermissions-*`) and `Keywords/utilities/Pbac.groovy` (`editPbacPermissions`, `uncheckAllEnabledPermissionCheckboxes`, `verifyPermissionsFunctional`). Suite membership: **`Test Suites/CRDC_PBAC.ts`** (unchecked order **TC11, TC15, TC14, TC13, TC12**) and **`CRDC_Regression.ts`** (TC11–TC15 in numeric order).

**Playwright command (target):** `pytest tests/Pbac -m CRDC_PBAC -k UncheckedPermissions` (serial, no `-n`). Full marker `pytest -m CRDC_PBAC` should still end with Master **EnableAllPermissions**.

Do **not** only add pytest files. `edit_pbac_permissions` and `verify_permissions_functional` currently raise `NotImplementedError` for `"negative"`.

---

## Why this is not a copy of TC06–TC10

Positive (TC06–TC10) **checks** every enabled box, then asserts handlers return **True**. Negative **unchecks** every enabled box, then asserts the same handlers return **False** (`correctly *not* accessible`).

The Excel driver is already scenario-aware (`list_internal_names_for_scenario` collects `unchecked` / `fixed_unchecked` for negative). Shared `_PERMISSION_FUNCTIONAL` handlers stay; only **edit UI**, **pass/fail polarity**, **Master-for-Admin**, and a few **early-False** paths need work.

---

## Current Playwright state

| Piece | Status |
|---|---|
| TC06–TC10 positive tests + handlers | Done (live dual-run vs Katalon 2026-11-09 matched keys / PASS / skip) |
| `list_internal_names_for_scenario(..., "negative")` | Ready |
| `_functional_data_submission_confirm` Submitter-negative branch | Ready |
| SR reopen `pytest.fail` if no Approved SR | Positive-only (safe for negative) |
| `ManageUsersPage.check_all_enabled_permission_checkboxes` | Positive only |
| `edit_pbac_permissions(..., "negative")` | **Blocked** (`NotImplementedError`) |
| `verify_permissions_functional(..., "negative")` | **Blocked** (`NotImplementedError`); asserts `result` only |
| `edit_pbac_permissions` editor role | Requires `hub.role == "Admin"` (TC13 needs **Master**) |
| Uncheck-all (twice, DCP SR View) | **Missing** |
| Tests TC11–TC15 | **Missing** |
| `DisableAllPermissions` SuiteSetup | Not in PW; Katalon has it. Prefer **EnableAll** last, plus **TC13 Admin restore** |

---

## Katalon cases vs intended Playwright files

Thin tests, same shape as TC06–TC10. Markers: `CRDC_PBAC` + `CRDC_Regression` (none of these are in Katalon smoke).

| Katalon | Role | Edit as | Verify as | Extra | PW file |
|---|---|---|---|---|---|
| TC11 | Fedlead | Admin | Fedlead (`switch_user`) | — | `tests/Pbac/test_TC11_CRDC-PbacUncheckedPermissions-Fedlead.py` |
| TC12 | Dcp | Admin | Dcp | Uncheck **twice** (SR View gated) | `...-Dcp.py` |
| TC13 | Admin | **Master** | Admin | End: Master `edit_pbac_permissions("Admin", "positive")` | `...-Admin.py` |
| TC14 | Submitter | Admin | Submitter | Confirm handler already has a negative branch | `...-Submitter.py` |
| TC15 | User | Admin | User | Negative list is mostly `fixed_unchecked` | `...-User.py` |

Negative Excel sheets are `{Role}-negative` after `write_expected`. Notification keys stay skipped with the same log line as positive.

---

## What “PASS” means

Same closures as positive. Katalon:

- **positive** and `result == true` → `[PASS] '{perm}' accessible as expected.`
- **negative** and `result == false` → `[PASS] '{perm}' correctly *not* accessible.`
- otherwise → `[FAIL] Unexpected result ...`

Handlers must **return False** when the control is absent, not time out. PW today `pytest.fail`s the **whole test** if a handler raises; Katalon `markFailed` and continues the permission loop. Prefer: catch inside the handler (already the pattern) so one missing locator does not abort the rest. Do not require continue-on-failure unless dual-run shows Katalon skipping past a FAIL that we need to match.

`fixed_checked` keys are **not** in the negative list. Negative does **not** re-assert remaining locked permissions still work.

---

## Implementation phases

### Phase 1 — Uncheck path (no live TC yet)

**Files:** `src/crdc_pw/pages/users.py`, `src/crdc_pw/utils/pbac_helpers.py`

1. `uncheck_all_enabled_permission_checkboxes()` — enabled + checked → uncheck (mirror `check_all_...`).
2. `apply_negative_permission_edit(role)` — find/edit → reset → find/edit → expand panels → **uncheck twice** → Save → snackbar gone. Katalon comment: second pass unchecks DCP **SR View** after higher boxes unlock it.
3. `edit_pbac_permissions`: implement `"negative"` (call the uncheck helper, `write_expected(f"{role}-negative")`). Allow editor `hub.role in ("Admin", "Master")`.
4. Unit/docstrings only; no Hub TC.

**Exit:** A later phase can call `edit_pbac_permissions(hub, "Fedlead", "negative")` without `NotImplementedError`.

---

### Phase 2 — Negative verify polarity + handler hygiene

**Files:** `src/crdc_pw/utils/pbac_helpers.py`, optional `tests/unit/test_pbac_sheet.py`

1. Remove the negative `NotImplementedError` in `verify_permissions_functional`.
2. Invert asserts: negative PASS when `not result`; keep skip for keys not in `_PERMISSION_FUNCTIONAL`.
3. Walk handlers for **raise vs False**:
   - Early `return False` when Create / Start SR is missing (cancel, review, confirm, submit) — already good.
   - Visibility checks (`is_nav_*`, `is_create_visible`, `is_request_access_button_visible`) should return False, not timeout the test.
   - SR view: permission-denied empty row already returns False (that is a **PASS** on negative).
   - Do **not** screenshot `PBAC_FAIL_*` on SR view when `n > 1` during negative unless that run is actually failing (optional rename later).
4. Optional unit: `write_expected(f"{role}-negative")` then `list_internal_names_for_scenario(role, "negative")` counts / contains `fixed_unchecked` where expected.

**Exit:** `verify_permissions_functional(hub, "Fedlead", "negative")` is callable; offline tests cover the driver.

---

### Phase 3 — TC11 Fedlead live (prove the stack)

**Files:** new `test_TC11_...-Fedlead.py` (copy TC06; `"negative"` + `UncheckedPermissions` in the name)

1. Admin `edit_pbac_permissions(..., "negative")` → `switch_user` Fedlead → `verify_permissions_functional(..., "negative")`.
2. Dual-run vs Katalon TC11 on the same profile (`CRDC_PROFILE=qa2` unless agreed otherwise). Audit: permission **list**, functional **PASS (not accessible)**, notification **skips**.
3. After a standalone TC11, Fedlead optional boxes stay **unchecked**. Restore with EnableAll or a later positive/TC13 restore before other suites.

**Exit:** TC11 keys/PASS/skip match Katalon. Fix handler False-vs-timeout issues here before cloning more tests.

---

### Phase 4 — TC12 Dcp, TC14 Submitter, TC15 User

Same Admin-edit + `switch_user` pattern as TC07 / TC09 / TC10.

| Case | Watch |
|---|---|
| TC12 Dcp | Double uncheck from Phase 1; `data_submission:admin_submit` must return False when Create is gone (or Admin Submit disabled after a gated flow). |
| TC14 Submitter | `data_submission:confirm` already short-circuits for Submitter+negative if Create is still present. Confirm Create is **unchecked** for Submitter after negative edit; if Create remains (unexpected), the existing branch still applies. `access:request` must be False. |
| TC15 User | No DS functional keys in the **positive** list; negative still iterates **unchecked / fixed_unchecked** manage/DS/nav keys and expects False. |

Dual-run each vs Katalon (same audit as TC11). Markers: `CRDC_PBAC`, `CRDC_Regression`.

**Exit:** Four of five unchecked roles match Katalon. Admin (TC13) still open.

---

### Phase 5 — TC13 Admin (Master + restore)

Katalon TC13:

1. Login **Master** → Manage Users → `editPbacPermissions("Admin", "negative")`
2. Login **Admin** → `verifyPermissionsFunctional("Admin", "negative")`
3. Login **Master** again → `editPbacPermissions("Admin", "positive")` so later cases still have an Admin who can Manage Users

Playwright:

1. Parametrize `hub` as **Master** (not Admin).
2. `edit_pbac_permissions(hub, "Admin", "negative")`
3. `switch_user(hub, "Admin")` then `verify_permissions_functional(..., "negative")`
4. `switch_user(hub, "Master")` then `edit_pbac_permissions(hub, "Admin", "positive")` (or `enable_all_permissions("Admin")` if that is equivalent enough; prefer the Katalon positive edit for oracle `{Admin}-positive` if anything later reads it)

Do **not** strip Admin as the Admin PBAC user (that is how TC08 positive works; it is wrong for uncheck).

**Exit:** TC13 matches Katalon; Admin can still open Manage Users after the test.

---

### Phase 6 — Suite wiring, restore, docs

1. `pytest -m CRDC_PBAC` collection: TC01–TC05 defaults, TC06–TC10 positive, TC11–TC15 negative, **EnableAllPermissions last** (existing conftest hook). Filename order is TC11…TC15; Katalon `CRDC_PBAC.ts` uses TC11, TC15, TC14, TC13, TC12. **Do not reorder pytest** unless dual-run of the full suite fails because of leftover permissions. Prefer EnableAll last + TC13’s Admin restore.
2. Standalone: `pytest tests/Pbac -m CRDC_PBAC -k UncheckedPermissions` (serial).
3. Update [onboarding.md](onboarding.md) PBAC section: TC11–TC15 table, Master for TC13, `-k UncheckedPermissions`, leftover-uncheck warning.
4. Dual-run full `CRDC_PBAC` vs Katalon `CRDC_PBAC.ts` if practical; otherwise TC11–TC15 plus EnableAll.
5. Out of scope here: TC16–TC17 manage-scope, notification suite, `DisableAllPermissions` unless EnableAll-last is not enough.

**Exit:** Docs and commands match how QA will run it; env is restored to “all optional checked” after a full PBAC marker run.

---

## Risks and lookouts

- **Handlers that wait 15s then fail** instead of returning False will make negative runs slow or abort. Probe timeouts (`PROBE_MS` / `is_visible()`) belong on “is this gated control present?” checks.
- **Create-dependent DS flows:** if Create is hidden, return False immediately. Do not upload metadata on negative unless the role still has Create (unexpected after uncheck-all).
- **DCP SR View:** skip the second uncheck and DCP View may stay checked → false **positive** on a negative list (handler True, scenario expects False).
- **Env leftover:** TC06–TC10 leave boxes checked; negative **reset + uncheck** is the first step. After negative-only runs, EnableAll before smoke/positives.
- **SR / DS seed:** reopen’s Approved-SR `pytest.fail` is positive-only. Negative reopen PASSes if Reopen is missing, even with zero Approved rows.
- **Serial only.** Shared PBAC users; no xdist.
- **QA vs QA2:** dual-run on the same profile as Katalon. Permission **keys** come from the post-edit Excel snapshot, not the Hub URL.

---

## Suggested live order

1. Phase 1–2 on a feature branch off `develop`.
2. Phase 3 TC11 + Katalon audit; fix handlers.
3. Phase 4 TC12 / TC15 (lighter DS) then TC14.
4. Phase 5 TC13 last.
5. Phase 6 docs + EnableAll confirmation.

Optional first slice: **Fedlead TC11 only** in a PR, then the other roles.

---

## Out of scope

- TC16 / TC17 manage-scope
- NotificationEmails (skipped keys stay skipped)
- Rewriting positive handlers for a separate “negative” map
- `docs/pbac-functional-refactor-plan.md` (removed; DOM already on page objects)
