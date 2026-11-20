# CI notes

CI is **GitHub Actions**, not Jenkins. The workflow is [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). It is `workflow_dispatch` only: the `unit` job always runs, and the live `smoke` job runs when you tick **run_smoke** (and pick the `profile`). Adding `pull_request` or a schedule is a later step.

## Gitignored yaml vs checkout

`config/dev.yaml`, `qa.yaml`, `qa2.yaml`, and `stage.yaml` are **not in git** (passwords and TOTP seeds). `actions/checkout` therefore does not give the runner those files.

| Job | What it uses |
|---|---|
| Unit | Committed `config/*.yaml.example` (URLs, empty secrets). `load_settings` falls back to the example when the real yaml is missing. |
| Smoke | A job step writes `config/<profile>.yaml` from GitHub Environment secrets, then pytest reads that file the same way a local run does. |

The app does **not** read GitHub secrets itself. Secrets become a yaml file on the runner, then disappear with the workspace.

## GitHub Environments

Create the Environments on the GitHub repo, named **`dev`**, **`qa`**, **`qa2`**, and **`stage`** (only the ones you run). In each one:

- **Variable** (optional): `BASE_URL` — only if you need to override the URL already in the example file.
- **Secrets**, Katalon names (same keys as the yaml):

  `AdminEmail`, `AdminPassword`, `AdminSecret`, `FedleadEmail`, `FedleadPassword`, `FedleadSecret`, `DcpEmail`, `DcpPassword`, `DcpSecret`, `SubmitterEmail`, `SubmitterPassword`, `SubmitterSecret`, `UserEmail`, `UserPassword`, `UserSecret`, `MasterEmail`, `MasterPassword`, `MasterSecret`

Leave a role's secrets unset if that environment should skip it.

For the upload CLI case (CRDCDH-1405 TC101) also set **`SubmitterApiToken`** (secret) and, only if the default is wrong, **`ApiUrl`** (variable; defaults to the Hub URL plus `api/graphql`). That test fails, not skips, when the token is empty, so a smoke job without it goes red on purpose. The smoke job needs Python 3.13 or newer (the CLI requires it; the check fails with a clear message otherwise). Like Katalon, every CLI run first runs `pip install -r tools/crdc-datahub-cli-uploader/requirements.txt --quiet` (3 minute timeout), so the job needs no separate install step for the CLI. The unit job stays on 3.11 and needs none of this.

## Smoke job

The `smoke` job in `ci.yml` is this, in order: write the yaml, run `bash ci/run_suite.sh CRDC_Smoke`, and upload `reports/` (HTML report, JUnit XML and failure screenshots). [`ci/run_suite.sh`](run_suite.sh) is the one command a pipeline needs: it runs `pytest -m CRDC_PBAC -k EnableAllPermissions` (the Katalon suite setup; if that fails it stops), then `pytest -m <marker>` serially (PBAC shares permissions, so no `-n`), writes `reports/junit-setup.xml` and `reports/junit.xml`, and exits with the suite's exit code. The marker defaults to `CRDC_Smoke`; extra arguments go to the suite run. Both runs pass `--tracing=off` and `test-results/` is not uploaded: a trace holds the Hub tab's network requests, and this repo is public, so its artifacts are downloadable by anyone signed in to GitHub. The workflow sets `permissions: contents: read`. One prerequisite is not automated: Data Explorer TC201 needs the `automation_CompletedStudy` study seeded on the environment (see the smoke plan).

```yaml
smoke:
  runs-on: ubuntu-latest
  environment: ${{ inputs.profile }}   # dev, qa, qa2, or stage
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
    - run: bash ci/run_suite.sh CRDC_Smoke   # EnableAllPermissions, then the suite, serial, no traces
      env:
        CRDC_PROFILE: ${{ inputs.profile }}
```

`write_profile_yaml.py` copies `config/<profile>.yaml.example` and overlays any of those env vars that are set. It prints how many roles were filled; it never prints secret values.

Do not commit filled yaml files or bake them into an image.

## Running from another pipeline (ctos-ghr-katalon-test)

The workflow in this repo is a standalone placeholder. The shared pipeline repo (`ctos-ghr-katalon-test`) will run these tests by checking this repo out. Its Katalon workflow keeps one secret per profile (`EXECUTION_PROFILE_<PROFILE>`, the whole `.glbl`) and writes it to `Profiles/`; this repo can be run the same way. The pipeline must:

1. Check out `CBIIT/crdc-dh-automation-pw` (a ref input). The upload CLI cases need **Python 3.13 or newer**; on an older Python those two tests fail with a clear message.
2. `pip install -r requirements.txt` (it contains `-e .`, so the same install step the Playwright workflow uses for `commons-automation` works) and `playwright install --with-deps chromium`.
3. Provide the credentials as `config/<profile>.yaml`, for `CRDC_PROFILE` = `dev`, `qa`, `qa2` or `stage` (map it from the pipeline's environment choice), in one of two ways:

   - **One secret per profile (recommended, like Katalon).** The secret holds the whole filled yaml, copied from `config/<profile>.yaml.example`. The pipeline writes it with `printf '%s' "$SECRET" > config/<profile>.yaml`. That is one secret per environment (for example `CRDC_PW_PROFILE_QA`, the name is the pipeline's choice) instead of 19 each.
   - **One secret per key.** Set these as environment variables and run `python ci/write_profile_yaml.py`, which fills the example and writes the same file:

     | Name | Kind | Needed for |
     |---|---|---|
     | `<Role>Email`, `<Role>Password`, `<Role>Secret` for `Admin`, `Fedlead`, `Dcp`, `Submitter`, `User`, `Master` | secrets | login (Login.gov plus TOTP seed) |
     | `SubmitterApiToken` | secret | upload CLI cases (the test fails without it) |
     | `BASE_URL` | variable, optional | only to override the URL in the example file |
     | `ApiUrl` | variable, optional | only if not `<base url>api/graphql` |

   Either way the file is gitignored and the app reads only that file. Delete it after the run if the runner is not thrown away.
4. Run `CRDC_PROFILE=<profile> bash ci/run_suite.sh <marker>` (marker defaults to `CRDC_Smoke`; extra arguments go to the suite run). It runs EnableAllPermissions, then the suite **serially** (never `-n`: PBAC shares permissions), with `--tracing=off`, and writes `reports/junit.xml`. Its exit code is the suite's.
5. Upload `reports/` (lower case, which differs from the `Reports/` folder `commons-automation` writes). Do not upload `test-results/`: it holds traces, and public-repo artifacts are downloadable by anyone signed in to GitHub.
6. Give the job `permissions: contents: read`.

Environment prerequisites that no pipeline sets up: Data Explorer TC201 needs the `automation_CompletedStudy` study seeded on the environment, and the Release Notes test (CRDCDH-4006) reads the release notes from a GitHub branch named like the profile, so a `dev` profile needs a `dev` branch there.

## Local vs Actions

```bash
# local — edit the gitignored file
cp config/qa.yaml.example config/qa.yaml
# fill secrets, then:
CRDC_PROFILE=qa pytest -m CRDC_Smoke

# Actions — same pytest command, after the write step above
```

Runner: Python 3.11+ and Chromium (`playwright install --with-deps chromium`, or `mcr.microsoft.com/playwright/python`, pinned to the Playwright version in `pyproject.toml`).
