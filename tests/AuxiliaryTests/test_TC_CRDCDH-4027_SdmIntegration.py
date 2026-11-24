"""Xray CRDCDH-4027 — Integrate CRDC Submission Model (SDM) into Data Hub (story CRDCDH-3921). Phase 1.

What this checks
    The Hub must show the new SDM model next to the existing ones (GC, CTDC, ICDC, PSDC) and let
    the user download SDM's documentation files from the Model Navigator. Phase 1 only reads and
    downloads; it creates nothing and needs no test data. Creating an SDM submission, validating
    metadata and the Data Explorer checks are later phases.

Where the expected values come from
    The Hub decides which models exist from cache/content.json on the tier branch (qa, qa2, dev)
    of CBIIT/crdc-datahub-models. The test fetches that file (crdc_pw.utils.model_content) and
    build the expected lists from it, so nothing is typed into the test and it keeps
    working when a model is added or its version changes. Per model the file gives a display
    name, an order, a current version and an isHidden flag.

Files this test downloads (all saved to test-results/downloads, nothing is kept in git)
    Model Navigator, SDM Model, "Available Downloads" menu:
      Data Dictionary  > All Properties (PDF | JSON | TSV)       SDM_Dictionary_All_<version>.pdf  .json  .tsv
      Data Dictionary  > Required Properties (PDF | JSON | TSV)  SDM_Dictionary_Required_<version>.pdf  .json  .tsv
      All Vocabularies (TSV)  and  All Vocabularies (JSON)       SDM_Controlled_Vocabularies<timestamp>.zip (two zips)
      Submission Templates > All Templates                       SDM_Data_Loading_Templates_<version>.zip
    That is 6 dictionary files, 2 vocabulary zips and 1 template zip.
    <version> is the model's current-version from the manifest (0.0.3 at the time of writing).

Flow (Admin, one login for the whole test):
  1. Header "Model Navigator" menu lists the visible models in manifest order, SDM Model
     included, and no model the manifest hides (CCDI, Test MDF, Hidden Model)
  2. Click SDM Model; the page heading is "SDM Data Model"
  3. Download the 6 Data Dictionary files; each is named for the SDM version and is not empty
  4. Download the 2 All Vocabularies zips; each is an SDM zip, a real zip archive, and not empty
  5. Download the All Templates zip; it is an SDM zip
  6. Open that zip and expect at least one template .tsv inside. TURNED OFF for now (see
     CHECK_TEMPLATE_ZIP_CONTENTS below): SDM is a skeleton model, so the zip is empty.

The other half of the story, the Create a Data Submission dialog, is in its own file,
test_TC_CRDCDH-4027_SdmCreateDialog.py, because it needs a Submitter login.

Not covered: "Example Templates" (SDM sets no loading file, so there is nothing to download, as
for PSDC) and the Hub hiding SDM (the test cannot edit the manifest; it only checks that models
the manifest hides are absent).
"""

from __future__ import annotations

import logging
import re
import zipfile

import pytest
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.model_navigator import ModelNavigatorPage
from crdc_pw.utils.model_content import (
    current_version,
    fetch_model_content,
    hidden_display_names,
    navigator_menu_label,
    visible_display_names,
)

log = logging.getLogger("crdc_pw.tc_crdcdh_4027")

SDM = "SDM"

# Step 6 opens the All Templates zip and expects template .tsv files in it. It is off because the
# SDM model is a skeleton for now: no node is marked Template: 'Yes', so the Hub builds an empty
# zip (22 bytes). The dev team confirmed this is expected for now. Set this to True once the SDM
# model has template nodes. Step 5 (the download works and the file is an SDM zip) still runs.
CHECK_TEMPLATE_ZIP_CONTENTS = False

pytestmark = pytest.mark.CRDC_Auxiliary


@pytest.mark.parametrize("hub", ["Admin"], indirect=True)
def test_TC_CRDCDH_4027_SdmInModelNavigator(hub: Hub) -> None:
    # Setup: read what the Hub is supposed to show. content is the parsed cache/content.json for
    # this profile's tier; version is SDM's current-version in it (for example "0.0.3").
    content = fetch_model_content(hub.settings.profile)
    version = current_version(content, SDM)
    header = HeaderPage(hub)

    # 1. Menu lists the visible models in manifest order, and none that the manifest hides.
    #    expected_items are labels like "GC Model", "CTDC Model", ..., "SDM Model": visible models
    #    sorted by the manifest's order field, each as "<display name> Model". The menu text is
    #    read from the page, so this compares what the user sees with what the manifest says.
    header.open_model_navigator_menu()
    items = header.read_model_navigator_items()
    expected_items = [navigator_menu_label(name) for name in visible_display_names(content)]
    assert items == expected_items, f"Model Navigator menu {items}, manifest says {expected_items}"
    # Explicit check for the story: SDM is in the menu.
    assert navigator_menu_label(SDM) in items
    # Models the manifest flags isHidden must not show up for users.
    for hidden in hidden_display_names(content):
        assert navigator_menu_label(hidden) not in items, f"hidden model {hidden!r} is in the menu {items}"

    # 2. Open SDM Model (route /model-navigator/SDM/<version>); the page heading identifies it.
    header.open_model_navigator_for(SDM)
    navigator = ModelNavigatorPage(hub)
    expect(navigator.title).to_have_text("SDM Data Model")

    # 3. Data Dictionary downloads: 2 scopes x 3 formats = 6 files. For each one the page object
    #    opens Available Downloads > Data Dictionary > "<scope> Properties (<kind>)", clicks it and
    #    saves the file the Hub sends. Expected names, with version 0.0.3:
    #      SDM_Dictionary_All_0.0.3.pdf   SDM_Dictionary_All_0.0.3.json   SDM_Dictionary_All_0.0.3.tsv
    #      SDM_Dictionary_Required_0.0.3.pdf  ... .json  ... .tsv
    #    The optional "v" in the pattern allows either 0.0.3 or v0.0.3 in the file name.
    #    The check is on the file name and size only; the contents are not opened.
    for scope in ("All", "Required"):
        for kind in ("PDF", "JSON", "TSV"):
            saved = navigator.download(f"{scope} Properties ({kind})", group="Data Dictionary")
            name_pattern = rf"SDM_Dictionary_{scope}_v?{re.escape(version)}\.{kind.lower()}"
            assert re.fullmatch(name_pattern, saved.name), f"{saved.name} does not match {name_pattern}"
            assert saved.stat().st_size > 0, f"{saved.name} is empty"

    # 4. Vocabularies: two items sit directly in the menu, "All Vocabularies (TSV)" and
    #    "(JSON)". Each downloads a zip named SDM_Controlled_Vocabularies<timestamp>.zip (the Hub
    #    puts a timestamp in the name, so only the prefix is checked, and the TSV and JSON zips
    #    have different sizes but the same name pattern). Checks: SDM prefix, .zip extension, a
    #    valid zip archive, and not empty. The files inside the zip are not listed.
    for kind in ("TSV", "JSON"):
        saved = navigator.download(f"All Vocabularies ({kind})")
        assert saved.name.startswith("SDM_Controlled_Vocabularies"), saved.name
        assert saved.suffix == ".zip", saved.name
        assert zipfile.is_zipfile(saved) and saved.stat().st_size > 0, f"{saved.name} is empty or not a zip"

    # 5. Submission Templates: Available Downloads > Submission Templates > All Templates. The Hub
    #    builds one zip with a loading template (one .tsv per node) for every node the data model
    #    marks as a template. Expected name: SDM_Data_Loading_Templates_<version>.zip.
    #    Only the download and the SDM name are checked while the zip is empty (see step 6).
    saved = navigator.download("All Templates", group="Submission Templates")
    assert saved.name.startswith("SDM_Data_Loading_Templates"), saved.name

    # 6. Open the zip and list the .tsv files in it. A usable SDM zip has one per template node.
    #    Skipped while CHECK_TEMPLATE_ZIP_CONTENTS is False (the skeleton SDM zip is empty).
    templates: list[str] = []
    if CHECK_TEMPLATE_ZIP_CONTENTS:
        with zipfile.ZipFile(saved) as archive:
            templates = [name for name in archive.namelist() if name.lower().endswith(".tsv")]
        assert templates, f"{saved.name} has no template TSV files ({saved.stat().st_size} bytes)"
    else:
        log.info(
            "Skip template zip contents check (skeleton SDM model): %s is %s bytes", saved.name, saved.stat().st_size
        )

    log.info(
        "PASS CRDCDH-4027 Model Navigator: SDM v%s, %s template file(s) checked, as %s on profile=%s",
        version,
        len(templates),
        hub.role,
        hub.settings.profile,
    )
