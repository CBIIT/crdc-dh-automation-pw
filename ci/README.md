# CI notes (Phase 0)

CI will be **GitHub Actions**, not Jenkins. The placeholder workflow is [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). It is `workflow_dispatch` only until the repo is on GitHub and we add `pull_request` / scheduled smoke.

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

## Smoke job (when you add it)

```yaml
smoke:
  runs-on: ubuntu-latest
  environment: ${{ inputs.profile }}   # qa, qa2, or stage
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - run: pip install -e .
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
      run: python ci/write_profile_yaml.py
    - run: pytest -m smoke --tracing=retain-on-failure
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
CRDC_PROFILE=qa pytest -m smoke

# Actions — same pytest command, after the write step above
```

Runner: Python 3.11+ and Chromium (`playwright install --with-deps chromium`, or `mcr.microsoft.com/playwright/python`, pinned to the Playwright version in `pyproject.toml`).
