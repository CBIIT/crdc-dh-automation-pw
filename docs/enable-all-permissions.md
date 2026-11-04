# EnableAllPermissions (Playwright)

**Implemented:** [tests/SuiteSetup/test_EnableAllPermissions.py](../tests/SuiteSetup/test_EnableAllPermissions.py) — Katalon `Test Cases/CRDC/SuiteSetup/EnableAllPermissions`.

Master signs in, opens Manage Users, and for Admin, Dcp, Fedlead, Submitter, and User runs `ManageUsersPage.enable_all_permissions` (reset → check all enabled checkboxes → Save). No Excel oracle; TC01 owns `PBACPermissions.xlsx` compare.

- Marker: `CRDC_PBAC` only.
- Full suite: `pytest -m CRDC_PBAC` collects `tests/Pbac/` then `tests/SuiteSetup/` (TC01 then restore). Run **serial** (no `pytest-xdist`).
- Isolated defaults check: `pytest -m CRDC_PBAC -k TC01` skips EnableAll.

Page helpers live in [src/crdc_pw/pages/users.py](../src/crdc_pw/pages/users.py): `check_all_enabled_permission_checkboxes`, `enable_all_permissions`.
