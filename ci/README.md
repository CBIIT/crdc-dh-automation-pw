# CI notes

CI is **GitHub Actions**, not Jenkins. The workflow is [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). It is `workflow_dispatch` only: the `unit` job always runs, and the live `smoke` job runs when you tick **run_smoke** (and pick the `profile`). Adding `pull_request` or a schedule is a later step.

## Gitignored yaml vs checkout

`config/qa.yaml`, `qa2.yaml`, and `stage.yaml` are **not in git** (passwords and TOTP seeds). `actions/checkout` therefore does not give the runner those files.

| Job | What it uses |
|---|---|
| Unit | Committed `config/*.yaml.example` (URLs, empty secrets). `load_settings` falls back to the example when the real yaml is missing. |
| Smoke | A job step writes `config/<profile>.yaml` from GitHub Environment secrets, then pytest reads that file the same way a local run does. |

The app does **not** read GitHub secrets itself. Secrets become a yaml file on the runner, then disappear with the workspace.

## GitHub Environments

Create three Environments on the GitHub repo, named **`qa`**, **`qa2`**, and **`stage`**. In each one:

- **Variable** (optional): `BASE_URL` — only if you need to override the URL already in the example file.
- **Secrets**, Katalon names (same keys as the yaml):

  `AdminEmail`, `AdminPassword`, `AdminSecret`, `FedleadEmail`, `FedleadPassword`, `FedleadSecret`, `DcpEmail`, `DcpPassword`, `DcpSecret`, `SubmitterEmail`, `SubmitterPassword`, `SubmitterSecret`, `UserEmail`, `UserPassword`, `UserSecret`, `MasterEmail`, `MasterPassword`, `MasterSecret`

Leave a role's secrets unset if that environment should skip it.

For the upload CLI case (CRDCDH-1405 TC101) also set **`SubmitterApiToken`** (secret) and, only if the default is wrong, **`ApiUrl`** (variable; defaults to the Hub URL plus `api/graphql`). That test fails, not skips, when the token is empty, so a smoke job without it goes red on purpose. The smoke job needs Python 3.13 or newer (the CLI requires it; the check fails with a clear message otherwise). Like Katalon, every CLI run first runs `pip install -r tools/crdc-datahub-cli-uploader/requirements.txt --quiet` (3 minute timeout), so the job needs no separate install step for the CLI. Set `CRDC_CLI_PYTHON` (env or profile yaml) to use another interpreter. Optional profile keys with the Katalon names: `CRDC_CLI_RETRIES`, `CRDC_CLI_OVERWRITE`, `CRDC_CLI_DRYRUN`, `CRDC_MANIFEST_ID_FIELD`. The unit job stays on 3.11 and needs none of this.

## Smoke job

The `smoke` job in `ci.yml` is this, in order: write the yaml, run `pytest -m CRDC_PBAC -k EnableAllPermissions` (suite setup), run `pytest -m CRDC_Smoke` serially (PBAC shares permissions, so no `-n`), and upload `reports/` and `test-results/` (traces). One prerequisite is not automated: Data Explorer TC201 needs the `automation_CompletedStudy` study seeded on the environment (see the smoke plan).

```yaml
smoke:
  runs-on: ubuntu-latest
  environment: ${{ inputs.profile }}   # qa, qa2, or stage
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.13"   # the upload CLI (1405 TC101) needs 3.13 or newer
    - run: pip install -e .   # the CLI case installs the CLI's requirements itself, before each run
    - run: playwright install --with-deps chromium
    - name: Write gitignored profile yaml from secrets
      env:
        CRDC_PROFILE: ${{ inputs.profile }}
        BASE_URL: ${{ vars.BASE_URL }}
        AdminEmail: ${{ secrets.AdminEmail }}
        AdminPassword: ${{ secrets.AdminPassword }}
        AdminSecret: ${{ secrets.AdminSecret }}
        FedleadEmail: ${{ secrets.FedleadEmail }}
        FedleadPassword: ${{ secrets.FedleadPassword }}
        FedleadSecret: ${{ secrets.FedleadSecret }}
        DcpEmail: ${{ secrets.DcpEmail }}
        DcpPassword: ${{ secrets.DcpPassword }}
        DcpSecret: ${{ secrets.DcpSecret }}
        SubmitterEmail: ${{ secrets.SubmitterEmail }}
        SubmitterPassword: ${{ secrets.SubmitterPassword }}
        SubmitterSecret: ${{ secrets.SubmitterSecret }}
        UserEmail: ${{ secrets.UserEmail }}
        UserPassword: ${{ secrets.UserPassword }}
        UserSecret: ${{ secrets.UserSecret }}
        MasterEmail: ${{ secrets.MasterEmail }}
        MasterPassword: ${{ secrets.MasterPassword }}
        MasterSecret: ${{ secrets.MasterSecret }}
        ApiUrl: ${{ vars.ApiUrl }}
        SubmitterApiToken: ${{ secrets.SubmitterApiToken }}
      run: python ci/write_profile_yaml.py
    - run: pytest -m CRDC_PBAC -k EnableAllPermissions
      env:
        CRDC_PROFILE: ${{ inputs.profile }}
    - run: pytest -m CRDC_Smoke
      env:
        CRDC_PROFILE: ${{ inputs.profile }}
```

`write_profile_yaml.py` copies `config/<profile>.yaml.example` and overlays any of those env vars that are set. It prints how many roles were filled; it never prints secret values.

Do not commit filled yaml files or bake them into an image.

## Local vs Actions

```bash
# local — edit the gitignored file
cp config/qa.yaml.example config/qa.yaml
# fill secrets, then:
CRDC_PROFILE=qa pytest -m CRDC_Smoke

# Actions — same pytest command, after the write step above
```

Runner: Python 3.11+ and Chromium (`playwright install --with-deps chromium`, or `mcr.microsoft.com/playwright/python`, pinned to the Playwright version in `pyproject.toml`).
