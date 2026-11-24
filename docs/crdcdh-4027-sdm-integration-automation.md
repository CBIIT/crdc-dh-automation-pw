# CRDCDH-4027 — Integrate CRDC Submission Model (SDM) into Data Hub: automation guide

Jira: story [CRDCDH-3921](https://tracker.nci.nih.gov/browse/CRDCDH-3921) (Ready for QA Testing, fix version CRDCDH 3.7.2),
test [CRDCDH-4027](https://tracker.nci.nih.gov/browse/CRDCDH-4027) (Manual, Open, Admin role, Major).
Supporting tasks, all Closed: CRDCDH-3930 (FE add model), CRDCDH-3934 (DATA add model to Model Repository),
CRDCDH-3961 (BE support data submissions for the model). Related precedent: CRDCDH-3182 and CRDCDH-3183 (PSDC integration).

This guide was updated on 24 Nov 2026 after reading the Hub source (`CBIIT/crdc-datahub-codebase`, branch `dev`, commit `0b2e05d`),
the model repository (`CBIIT/crdc-datahub-models`, tier branches) and the SDM model repo (`CBIIT/crdc-submission-model`, `main`, 0.0.3).
Statements marked "not verified" were not checked on a live Hub.

## Phase 1 status (implemented on branch `feat/crdcdh-4027-sdm-integration`)

Phase 1 (read-only checks) is in `tests/AuxiliaryTests/test_TC_CRDCDH-4027_SdmIntegration.py`, marker `CRDC_Auxiliary`. Phases 2 to 4 below are still to do.
The sections further down that mention a PDF export with an `SDM_` prefix are superseded by what was found on the live Hub:

- **Downloads.** Model Navigator has an "Available Downloads" menu, not a single PDF button. SDM files are `SDM_Dictionary_{All|Required}_v?0.0.3.{pdf|json|tsv}`,
  two `SDM_Controlled_Vocabularies...zip` files and `SDM_Data_Loading_Templates...zip`. The test checks the name pattern and that each file is non-empty.
- **Menu and Create dialog.** Both are compared with the manifest (`cache/content.json` on the tier branch), fetched by `utils/model_content.py`. Hidden models must not appear.
  The Create dialog list must end with SDM, after PSDC.
- **Empty template zip (expected for now).** `SDM_Data_Loading_Templates_0.0.3.zip` is a 22-byte empty zip on QA, because no SDM node has `Template: 'Yes'` in the model.
  The dev team confirmed this is expected while SDM is a skeleton model. The zip contents check (step 6) is turned off with `CHECK_TEMPLATE_ZIP_CONTENTS = False` in the test;
  the download and the SDM file name are still checked. Turn it on when SDM gets template nodes.
- **QA2 does not show SDM yet.** The manifest on branch `qa2` lists SDM, but the QA2 Hub menu and Create dialog do not. The backend caches the manifest (24 hour TTL),
  so this may clear by itself, or the QA2 deploy may not have the model. The menu, navigator and dialog tests fail on QA2 for this reason.
- **Google Fonts.** The Model Navigator chunk imports a stylesheet from `fonts.googleapis.com`. If that host is unreachable, the page shows "Unexpected Application Error!"
  ("Unable to preload CSS"). Run the tests on a network that can reach it. This was seen on a restricted local network.

---

## 1. The change (CRDCDH-3921), as implemented

User need: a data submitter wants one submission data model, so they can reformat metadata once and submit it to several data commons.

The new model is the CRDC Submission Data Model, abbreviated **SDM**. The important finding from the code is that the Hub is
now **data driven**: the list of data models comes from a manifest, not from code. Adding SDM was mostly a data change.

### 1.1 Where models come from

| Piece | What it does |
|---|---|
| `CBIIT/crdc-datahub-models`, file `cache/content.json` on a **branch named after the tier** (`dev`, `qa`, `qa2`, `stage`, `prod`) | The manifest. One entry per model: `display-name`, `order`, `current-version`, `versions`, `isHidden`, model files, `model-navigator-config` (page title, PDF prefix, icons, filters), `semantics`. Model files live beside it in `cache/<model>/<version>/`. |
| Frontend `DataModelsContext` | Fetches `raw.githubusercontent.com/CBIIT/crdc-datahub-models/<tier>/cache/content.json` on every mount (cached copy served first). Sorts by `order`. `visibleModels` is every model where `isHidden` is not true. |
| Backend `data-model-service` (3.7.2) | Reads the same file through the `MODEL_CONTENT` config (`ttl_minutes` 1440, so up to 24 hours stale). Builds `hiddenDataModels` from `isHidden: true` and filters them out of lists. Migration `documentation/3-7-2/initialize-model-content-config.js`. |
| Backend `data-commons-display-names-map` | Only maps `CDS` to `GC`. Every other model shows its handle, so SDM shows "SDM". |

### 1.2 What the requirements mean in the code

| Requirement | Implementation |
|---|---|
| Model Navigator shows SDM | `useHeaderLinks` builds the **Model Navigator header dropdown** from `visibleModels`: one item per model, id `model-navigator-<name>`, text `<displayName> Model` (so "SDM Model"), link `/model-navigator/SDM/latest`. The page title comes from `model-navigator-config.pageTitle` = "SDM Data Model". |
| SDM in the Create dialog Data Commons dropdown, at the bottom, below PSDC | `CreateDataSubmissionDialog` maps `visibleModels`. Position comes from `order`: SDM is **6**, PSDC **5**, ICDC 4, CTDC 3, CCDI 2 (hidden), GC 1. |
| Header DATA COMMONS reads "SDM" | Submission `dataCommonsDisplayName`, which is the handle because there is no mapping. |
| Step 1 UPLOAD METADATA shows "SDM Data Model" | `MetadataUpload.tsx`: element `data-testid="metadata-upload-model-version"` with text `<dataCommonsDisplayName> Data Model: <link>`, where the link text is the model version with a `v` prefix (for example "v0.0.3"). Shown only when the submission has a model version. |
| Validation against SDM | Validator reads `content.json` model files (`ModelFactory`). Hidden models are still valid targets. |
| Data Explorer Data Commons dropdown shows SDM | The options are the **distinct data commons of released study nodes** (`dao/release.js`). SDM appears **only after at least one SDM submission has been released**. The table column is `dataCommonsDisplayNames` joined by ", ". |
| "Hide the integration, like PSDC" | Set `isHidden: true` on the model's entry in `content.json`. The model then disappears from the header Model Navigator menu, the Create dialog, the user profile Data Commons list and the Model Navigator route (an unlisted model raises "Unable to show the requested data model"), while the backend still treats the name as valid. Today on `qa` that is how CCDI, Test MDF and Hidden Model are hidden. PSDC is **not** hidden on dev, qa or qa2. |

### 1.3 SDM state per tier (content.json, checked 24 Nov 2026)

| Branch | SDM entry | Notes |
|---|---|---|
| `dev`, `qa`, `qa2` | `order` 6, `display-name` "SDM", `current-version` **0.0.3**, versions 0.0.3 and 0.0.2, `isHidden` unset (visible) | `qa` commit 2026-11-20. Visible models in order: GC, CTDC, ICDC, PSDC, SDM. Hidden: CCDI, Test MDF, Hidden Model. |
| `stage`, `prod` | No SDM entry | `STAGE-INIT-SDM` and `PROD-INIT-SDM` branches carry SDM 0.0.2 with no `order` or `display-name`. Not live yet. |

SDM model (`crdc-submission-model`, handle `SDM`, version 0.0.3): 17 top-level entries under `Nodes` as parsed
(biospecimen, case, demographics, diagnosis, exposure, family_history, followup, imaging, na, occurrence, participant,
personnel, program, publication, study, treatment, vitals) and one relationship (`of_study`). `example_submission_sheet.tsv` is empty.

The SDM manifest entry sets `readme-file`, `release-notes` and `loading-file` to empty strings. Consequences for Model Navigator downloads
(the Jira "all downloads should work" item):
- README: not configured, so no README to download.
- Loading example file: not configured, so no example download.
- Version History tab: the code falls back to `.../SDM/<version>/version-history.md`, which is not in the repo. The code tolerates a failed fetch (tab simply absent), so this is not an error to assert on.
- PDF export: configured (`pdfConfig.prefix` and `downloadPrefix` "SDM_"). This is the download that can be asserted: a file whose name starts with `SDM_`.
- Per-node and per-property template downloads come from the shared Model Navigator library. Not verified; find them in Step 0.

Possible content problems to raise (not for the test to assert): the SDM manifest `semantics` (`main-nodes` with `specimen`, `data_file`,
`study_personnel`; `file-nodes.data_file`) and `iconMap` (`Administrative`, `Subject`, `Visit`, `Data_File`) look copied from PSDC. SDM has no `data_file`
or `specimen` node in its model file, so file-node features and icons may not match. Ask the story owner.

## 2. How CRDCDH-4027 tests it

One manual step. Preconditions: open Hub QA, dismiss the warning banner, log in as **Admin** through any IdP, complete MFA, grant consent, open
**Model Navigator**, then check the expected results. The Jira step lists "QA Env" and "QA2 Env" with the same URL (`hub-qa`); QA2 is `hub-qa2`.
Run the Playwright test on both profiles.

| # | Expected result in Jira | What it proves | Automatable now? | Oracle |
|---|---|---|---|---|
| 1 | Integration can be hidden like PSDC | Hidden flag is honored | Partly. The test cannot edit `content.json`, but it can assert that **every model marked hidden** in the manifest is absent from the UI, and every visible one is present | `content.json` for the tier |
| 2 | SDM Data Model in Model Navigator | Manifest entry, model files load | Yes | "SDM Model" menu item; page title "SDM Data Model" |
| 3 | "SDM" in Create dialog Data Commons dropdown | `visibleModels` | Yes | Visible display names sorted by `order` |
| 4 | New submission header DATA COMMONS "SDM" | Backend stores `dataCommons=SDM`, FE shows it | Yes | "SDM" |
| 5 | Step 1 UPLOAD METADATA reads "SDM Data Model" | Submission model version set | Yes | `metadata-upload-model-version` text; version = `v` + `current-version` |
| 6 | Hub validates against SDM | Validator loads SDM files | Yes, needs data | Expected Validation Results TSVs |
| 7 | Data Explorer filter and column show SDM | Release data plus display name | Yes, **needs a released SDM study** (seed) | "SDM" option and column cell |
| 8 | All Model Navigator downloads work | Model assets reachable | Partly: PDF download, `SDM_` prefix, non-empty | Download file |
| 9 | Abbreviation is "SDM" | Naming | Covered by 2, 3, 4, 5, 7 | |
| 10 | SDM at the bottom, below PSDC | `order` | Yes | SDM index is last and after PSDC |

Not in the manual test (optional in the automated one):
- Validation actually **rejects** bad data. Use one TSV with a known error and an expected Validation Results file.
- The dropdown matches the manifest exactly (item 3 oracle), so a model dropped by mistake is caught.

## 3. Fit with this repo

Rules to follow (`.cursor/rules/crdc-dh-automation-pw.mdc`, `hybrid-pom-katalon-reuse.mdc`): the test owns the scenario and expected values;
pages read the UI; YAML holds locators; no `keywords/`; no `except: pass` on a required wait.

Already works for SDM, no change needed:
- `DataSubmissionsListPage.create_data_submission("New", "metadata only", "SDM", study)`. The option is matched by exact text (`_click_option_exact`).
- `DataSubmissionDetailPage.read_summary_header()` and `verify_summary_header_fields({"data_commons": "SDM"}, ...)` (partial mapping is allowed).
- `upload_folder`, `click_validate`, `verify_validation_results_vs_expected_for_tc(tc, model="SDM")`.
- `utils/validation_results.node_from_filename`: `SDM_diagnosis_v0.0.3.tsv` gives node `diagnosis`.
- `DataExplorerListPage.open()` and `Filters.yaml: DataCommons-Ddn` (`data-commons-display-names-select`).
- `Desktop.yaml: ModelNavigator-Tab` (`navbar-dropdown-model-navigator`) exists. `HeaderPage` has no method for it.

Missing:

| Gap | Where | Work |
|---|---|---|
| `utils/model_content.py`: fetch and parse `content.json` for the profile's tier branch | new, follows the raw GitHub fetch in `utils/static_content.py` | New. Pure functions are unit tested. |
| `HeaderPage` methods for the Model Navigator menu | `pages/header.py` | New: open menu, read items, click an item |
| `ModelNavigatorPage` (title, PDF download) | new `pages/model_navigator.py` | New, small |
| Read Create dialog Data Commons options | `pages/data_submissions_list.py` | New method |
| Read step 1 model line | `pages/data_submission_details.py` | New method; locator is known |
| Data Explorer: read filter options, filter by Data Commons, read headers and rows | `pages/data_explorer_list.py` | New methods (reuse `BasePage` table readers) |
| `SDM` sheet in `InputFiles/CRDC/DataSubmissionValidation/DSV_ValidationResults-mappings.xlsx` | data file | New. Sheets today: GC, ICDC, CTDC, PSDC. Without it `load_validation_results_mappings("SDM")` logs "Sheet not found". |
| SDM metadata and expected results | `InputFiles/CRDC/MetadataData/CRDCDH-4027/` | New |
| Seed study for Data Explorer | QA data | Manual prerequisite (Step 8) |

## 4. Proposed test layout

Follow the CRDCDH-4006 precedent (an Xray test of a story, no Katalon equivalent): one module under `tests/AuxiliaryTests/`, marker `CRDC_Auxiliary`.
Do not add `CRDC_Smoke` until the team decides it belongs.

```
tests/AuxiliaryTests/test_TC_CRDCDH-4027_SdmIntegration.py
    test_TC_CRDCDH_4027_SdmInModelNavigator          Admin      Jira results 1 (menu part), 2, 8, 9
    test_TC_CRDCDH_4027_SdmCreateAndValidate         Submitter  Jira results 1 (dialog part), 3, 4, 5, 6, 9, 10
    test_TC_CRDCDH_4027_SdmInDataExplorer            Submitter  Jira results 7, 9
```

One function per screen gives an independent pass/fail each, and the two read-only screens do not wait for validation.

Roles: Jira says Admin. Model Navigator is fine as Admin. Every existing DS flow test creates and validates as **Submitter**, so keep that for the
create/validate test. Before relying on it, confirm Admin lacks no permission on the same flow (see `tests/Pbac/`). If Admin should cover create too,
parametrize `hub` with `["Admin", "Submitter"]`.

The create/validate test writes one new submission with the generated 25-character name (as TC01 CRDCDH-697 does), so it is safe to rerun.

## 5. Implementation steps

Do these in order. Run `ruff check src tests`, `mypy` and `pytest tests/unit -m unit` at the end.

### Step 0 — Confirm the remaining locators on a live Hub (about 20 minutes)

Most locators are now known from the source. Confirm these on QA with `--headed` and `page.pause()` or `playwright codegen`:

| Item | Known from source | To confirm |
|---|---|---|
| Model Navigator tab | `//*[@id='navbar-dropdown-model-navigator']` (already in `Desktop.yaml`) | Opens on click or on hover |
| SDM menu item | id `model-navigator-SDM`, text "SDM Model" | Exact element is a link or a wrapper |
| Model Navigator page title | text "SDM Data Model" from `pageTitle` | Which element shows it (add a `data-testid` if there is one) |
| PDF download control | `pdfConfig` prefix `SDM_` | Button selector and filename |
| Node or property template downloads | Shared library | Whether any exist and what they are named |
| Create dialog options | `role=option`, text is the display name | Already covered by `Create.yaml: DataCommonsDdn-Option` |
| Step 1 model line | `data-testid="metadata-upload-model-version"` | Text for a new SDM submission, expected "SDM Data Model: v0.0.3" |
| Data Explorer option | `data-testid="data-commons-display-names-option-SDM"` | Visible after the seed study is released |
| Data Explorer table header and cell | Column is `dataCommonsDisplayNames` | Header text ("Data Commons") |

Add them to YAML (one-line comment naming the screen):

```
locators/CRDC/AILocators/Global/Header/Desktop/Desktop.yaml     # add ModelNavigator-Item with a {name} placeholder
locators/CRDC/AILocators/ModelNavigator/ModelNavigator.yaml     # new: Title, PdfDownload-Btn
locators/CRDC/AILocators/DataSubmissions/Detail/UploadMetadata/UploadMetadata.yaml   # new: ModelVersion-Lbl (testid above)
locators/CRDC/AILocators/DataExplorer/List/Filters/Filters.yaml # add DataCommons-Option with a {name} placeholder
```

Placeholders work as in `StudyView.yaml: NodeType-Option` (`{node}`). Run `tests/unit/test_locator_contract.py` and `test_locator_loader.py` after editing.

### Step 1 — Oracle from the manifest: `utils/model_content.py`

Pure helpers, no browser:

```python
"""Hub model manifest (crdc-datahub-models, <tier>/cache/content.json).

The Create dialog, the Model Navigator menu and the user profile list models from this file.
Tests build their expected lists from it, so the test does not hard code which models exist.
"""

CONTENT_URL = "https://raw.githubusercontent.com/CBIIT/crdc-datahub-models/{tier}/cache/content.json"

def fetch_model_content(profile: str) -> dict[str, dict]:
    """content.json for the tier branch that matches the profile (dev, qa, qa2)."""

def visible_display_names(content: dict[str, dict]) -> list[str]:
    """display-name (or the key) of every model whose isHidden is not true, sorted by order; models without order keep file order, after those with one."""

def hidden_display_names(content: dict[str, dict]) -> list[str]:
    """display-name of every model whose isHidden is true."""

def current_version(content: dict[str, dict], model: str) -> str:
    """current-version of the model entry."""
```

Sort exactly like the frontend `buildDataModels`: models with a finite `order` first, ascending; the rest keep manifest order.
Profile to branch is the same mapping the static-content tests use (qa2 to branch `qa2`). Add `tests/unit/test_model_content.py` with a small sample
(ordering, hidden filtering, missing `order`, missing `display-name`).

Caveat: the Hub frontend refetches the manifest on each load, but the backend caches it up to 24 hours. After someone changes `content.json`,
validation and display names may lag, so a failure right after a manifest change is not necessarily a bug.

### Step 2 — Header: Model Navigator menu

`pages/header.py`:

```python
_MODEL_NAVIGATOR = "CRDC/AILocators/Global/Header/Desktop/ModelNavigator-Tab"
_MODEL_NAVIGATOR_ITEM = "CRDC/AILocators/Global/Header/Desktop/ModelNavigator-Item"   # //*[@id='model-navigator-{name}']

def open_model_navigator_menu(self) -> None:
    """Open the Model Navigator header menu (click, or hover if that is how it opens)."""

def read_model_navigator_items(self) -> list[str]:
    """Texts of the model items in the open menu, in order (for example 'GC Model', 'SDM Model')."""

def open_model_navigator_for(self, name: str) -> None:
    """Click the menu item for a model handle and wait for the Model Navigator route."""
```

### Step 3 — `ModelNavigatorPage`

New `src/crdc_pw/pages/model_navigator.py`, with a module docstring and a plain-sentence docstring on each public method:

```python
"""Model Navigator (route /model-navigator/<model>/<version>).

Tests construct ModelNavigatorPage(hub) after opening a model from the header menu, then:
  title            - page title locator
  download_pdf()   - click the PDF export, return the saved path
"""

class ModelNavigatorPage(BasePage):
    @property
    def title(self) -> Locator: ...
    def download_pdf(self) -> Path: ...
```

Download pattern: copy `DataSubmissionDetailPage.export_validation_results_and_verify_filename` (`page.expect_download()`, saved under
`test-results/downloads`). The page returns the path; the **test** checks name prefix `SDM_` and size. Add node/property template downloads only if Step 0 finds them.

### Step 4 — Create dialog options

`pages/data_submissions_list.py`:

```python
def read_create_dialog_data_commons_options(self) -> list[str]:
    """Open Create a Data Submission, return the Data Commons options in order, close the dialog."""
```

Click `CREATE_BTN`, click `DATA_COMMONS_DDN`, wait for the first `DATA_COMMONS_OPTION`, read each via `_inner_text`, then close (Escape for the
dropdown, then the dialog's Cancel or Escape; confirm in Step 0). Keep it separate from `create_data_submission`.

### Step 5 — Step 1 model line

`pages/data_submission_details.py`: expose the locator as a property so the test can use `expect`:

```python
@property
def upload_model_version(self) -> Locator:
    """Step 1 UPLOAD METADATA line, for example 'SDM Data Model: v0.0.3'."""
    return self._loc(UPLOAD_MODEL_VERSION)
```

### Step 6 — Data Explorer reads

`pages/data_explorer_list.py`, reusing `BasePage` readers:

```python
def read_data_commons_options(self) -> list[str]:
    """Open the Data Commons filter, return the option texts (without All), close it."""

def apply_data_commons_filter(self, name: str) -> None:
    """Choose one Data Commons and wait for the table to reload."""

def read_table_headers(self) -> list[str]: ...
def read_table_rows(self) -> list[list[str]]: ...
```

Select the option the way `DataSubmissionsListPage._select_list_option` does (including the backdrop-click fallback described there).

### Step 7 — Metadata, expected results, mapping sheet

1. Create `InputFiles/CRDC/MetadataData/CRDCDH-4027/` with upload TSVs named `SDM_<node>_v0.0.3.tsv`. Take columns from
   `crdc-submission-model/model-desc/crdc-submission-model.yml` (node `Props`) and `crdc-submission-model-properties.yml` (required flags and enums).
   `example_submission_sheet.tsv` is empty, so build rows from the properties file. Start with a small valid set: `program`, `study`, `participant`, `diagnosis`.
   Add one file with a deliberate error (for example a value outside an enum) for the negative check.
2. Create `expected-ValidationResults/SDM_<node>_v0.0.3_expected-ValidationResults.tsv` for each file that should produce issues. Copy the column layout from
   `CRDCDH-887_TC101` or `TC08`.
3. Add an `SDM` sheet to `DSV_ValidationResults-mappings.xlsx`: column A node, column B the submitted-identifier column for that node (the key property of each node in the model).
   The Katalon repo has its own copy; update it only if a Katalon SDM case is planned.
4. Pin the model version in the file names. If `current-version` moves past 0.0.3, the step 1 oracle moves (it reads the manifest) but the files still validate against the version the submission was created with.

### Step 8 — The test module

`tests/AuxiliaryTests/test_TC_CRDCDH-4027_SdmIntegration.py`. Module docstring with a Flow list, numbered step comments, a PASS log line at the end (as CRDCDH-4006 does).

```python
"""Xray CRDCDH-4027 - Integrate CRDC Submission Model (SDM) into Data Hub (story CRDCDH-3921).

Expected models come from the Hub manifest (crdc-datahub-models <tier>/cache/content.json), so
the lists below follow what the Hub is configured to show for this profile.

Flow (Model Navigator, Admin):
  1. Menu lists every visible model and no hidden one; SDM Model is present
  2. Open SDM Model; the page title is 'SDM Data Model'
  3. PDF export downloads a non-empty file whose name starts with SDM_
Flow (Create and validate, Submitter):
  1. Create dialog options equal the visible models in manifest order; SDM is last, after PSDC
  2. Create a New SDM metadata-only submission; header Data Commons is SDM
  3. Step 1 line reads 'SDM Data Model: v<current version>'
  4. Upload, validate, compare Validation Results with the expected TSVs
Flow (Data Explorer, Submitter):
  1. Data Commons filter offers SDM (needs a released SDM study, see seed note)
  2. Filtered rows show SDM in the Data Commons column and include the seed study
Seed (manual, as CRDCDH-3026 does): release one SDM submission for study SDM_STUDY on each profile.
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.pages.data_explorer_list import DataExplorerListPage
from crdc_pw.pages.data_submission_details import DS_AUTOMATION_STUDY_CREATE, DataSubmissionDetailPage
from crdc_pw.pages.data_submissions_list import DataSubmissionsListPage
from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.model_navigator import ModelNavigatorPage
from crdc_pw.utils.model_content import (
    current_version,
    fetch_model_content,
    hidden_display_names,
    visible_display_names,
)

log = logging.getLogger("crdc_pw.tc_crdcdh_4027")

TC_NAME = "CRDCDH-4027"
SDM = "SDM"
SDM_STUDY = "automation_SdmStudy"   # seed study, name to be agreed with the team

pytestmark = pytest.mark.CRDC_Auxiliary


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC_CRDCDH_4027_SdmInModelNavigator(hub: Hub) -> None:
    content = fetch_model_content(hub.settings.profile)
    header = HeaderPage(hub)

    # 1. Menu: visible models present, hidden models absent
    header.open_model_navigator_menu()
    items = header.read_model_navigator_items()
    assert f"{SDM} Model" in items
    for name in visible_display_names(content):
        assert any(item.startswith(name) for item in items), f"{name} missing from {items}"
    for name in hidden_display_names(content):
        assert not any(item.startswith(name) for item in items), f"hidden {name} shown in {items}"

    # 2. Open SDM; the page title shows the model
    header.open_model_navigator_for(SDM)
    nav = ModelNavigatorPage(hub)
    expect(nav.title).to_contain_text("SDM Data Model")

    # 3. PDF export
    saved = nav.download_pdf()
    assert saved.name.startswith("SDM_"), saved.name
    assert saved.stat().st_size > 0


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC_CRDCDH_4027_SdmCreateAndValidate(hub: Hub) -> None:
    content = fetch_model_content(hub.settings.profile)
    ds_list = DataSubmissionsListPage(hub)
    ds_list.open()

    # 1. Dropdown equals the visible models in manifest order; SDM last, after PSDC
    options = ds_list.read_create_dialog_data_commons_options()
    assert options == visible_display_names(content), options
    assert options[-1] == SDM
    assert options.index("PSDC") < options.index(SDM)

    # 2. Create a New SDM metadata-only submission; header shows SDM
    submission_name = ds_list.create_data_submission("New", "metadata only", SDM, DS_AUTOMATION_STUDY_CREATE)
    detail = DataSubmissionDetailPage(hub)
    detail.verify_summary_header_fields({"data_commons": SDM, "submission_name": submission_name})

    # 3. Step 1 UPLOAD METADATA names the model and its current version
    expect(detail.upload_model_version).to_have_text(f"{SDM} Data Model: v{current_version(content, SDM)}")

    # 4. Upload, validate, compare Validation Results
    detail.upload_folder(TC_NAME)
    detail.click_validate()
    detail.verify_validation_results_vs_expected_for_tc(TC_NAME, model=SDM)

    log.info("PASS CRDCDH-4027: SDM create and validate as %s on profile=%s", hub.role, hub.settings.profile)


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC_CRDCDH_4027_SdmInDataExplorer(hub: Hub) -> None:
    explorer = DataExplorerListPage(hub)

    # 1. Filter offers SDM
    explorer.open()
    assert SDM in explorer.read_data_commons_options(), "no released SDM study: seed missing"

    # 2. Filter to SDM; every row says SDM and the seed study is listed
    explorer.apply_data_commons_filter(SDM)
    column = explorer.read_table_headers().index("Data Commons")
    rows = explorer.read_table_rows()
    assert rows, "no SDM rows in Data Explorer"
    assert all(SDM in row[column].split(", ") for row in rows)
    assert any(SDM_STUDY in cell for row in rows for cell in row)
```

Notes:
- `to_have_text` is exact. If the version link adds whitespace, use `to_contain_text` or a regex.
- The dialog list equals the manifest list in order only if nothing else filters or reorders it for the role (user profile Data Commons does not restrict the dialog in the code read). If a role sees a subset, compare as a subsequence.
- Do not put the expected lists in the pages. The test passes the case data; pages only read.
- The file name keeps the Xray id, like `test_TC_CRDCDH-4006_ReleaseNotesPage.py`.

### Step 9 — Seed data for Data Explorer

The Data Explorer filter lists only data commons with **released** study data, so both the dropdown and the table check need a seed
(CRDCDH-3026 TC201 does the same with `automation_CompletedStudy`). Per profile (QA, QA2): create a study such as `automation_SdmStudy`, create an
SDM submission for it, upload the `CRDCDH-4027` metadata, validate, submit, release it, and put the study name in `SDM_STUDY`. Document the seed in
the module docstring. The test fails with "seed missing" when it is absent, it does not skip.

### Step 10 — Run and review

```bash
pytest tests/AuxiliaryTests -m CRDC_Auxiliary -k CRDCDH_4027 --headed        # QA (default)
CRDC_PROFILE=qa2 pytest tests/AuxiliaryTests -m CRDC_Auxiliary -k CRDCDH_4027
ruff check src tests && mypy
pytest tests/unit -m unit
```

Run three times on QA and once on QA2 before treating it as stable. Likely flake points: the Model Navigator menu opening, the PDF download, the validation wait.
Add a row under "Already `CRDC_Auxiliary` in Playwright but not in the Katalon suite" in `docs/auxiliary-suite-port-plan.md`.

## 6. Open questions for the story owner

1. **Hidden integration.** Confirmed by the code as `isHidden: true` in `content.json`. Is the intent that SDM ships hidden on stage and prod first (it has no entry there yet), and visible on dev, qa and qa2 now? If so the stage and prod checks are the inverse of this test (SDM absent).
2. **Content problems.** The SDM `semantics` and `iconMap` in the manifest look copied from PSDC and do not match the SDM nodes (no `data_file`, `specimen` or `study_personnel`). Is that intended? It may break metadata-and-data-files submissions and Data Explorer node types for SDM.
3. **Model Navigator downloads.** SDM sets no README, loading example or release notes. Is that intended, and is the PDF the only download to verify? Any node or property templates?
4. **Seed.** Who creates and refreshes the released SDM study on QA and QA2, and what is it called?
5. **Role.** Jira says Admin throughout. Is Submitter-created validation acceptable, or must Admin create the SDM submission?
6. **QA2.** The Jira test lists the QA URL twice. Should QA2 run the same checks?
7. **Metadata.** Who supplies valid and invalid SDM TSVs and the expected Validation Results? `example_submission_sheet.tsv` in the model repo is empty, and the SDM mapping sheet needs the key column for each node.
8. **Backend cache.** The backend reads the manifest with a 24 hour TTL. After a manifest change, is there a way to force a refresh on QA before the run?

## 7. Definition of done

- Three tests pass on QA and QA2 as described, or are explicitly deferred for an open question.
- New locators are YAML only; tests import no `CRDC/...` strings.
- Pages read the UI; tests (and `utils/model_content.py`) hold expected values.
- `utils/model_content.py` has unit tests in `tests/unit/`.
- `SDM` mapping sheet and `CRDCDH-4027` metadata folder are committed. No credentials, `auth/**` or `config/qa.yaml` committed.
- Row added to `docs/auxiliary-suite-port-plan.md`. Xray CRDCDH-4027 marked automated once the tests are stable.
