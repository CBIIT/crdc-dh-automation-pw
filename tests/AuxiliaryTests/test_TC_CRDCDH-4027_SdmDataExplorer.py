"""Xray CRDCDH-4027 — SDM in the Data Explorer Data Commons filter and column (story CRDCDH-3921). Phase 4.

What this checks
    Once an SDM study has been released, Data Explorer must offer SDM in its Data Commons filter,
    and filtering by SDM must list only studies whose Data Commons column includes SDM, with the
    released SDM study among them. This is Jira expected result 7 of CRDCDH-4027.

Why it is turned off for now (RUN_SDM_DATA_EXPLORER_TEST)
    The Data Commons filter only lists data commons that have released study data. To get SDM
    there, someone must create an SDM submission, upload valid metadata, validate, submit and
    release it. The Hub cannot do that for SDM yet (every real SDM upload fails with "Batch
    validation failed - internal error", see test_TC_CRDCDH-4027_SdmCreateAndValidate.py), so on
    QA on 24 Nov 2026 the filter offers only CTDC and GC. While the flag is False the test is
    reported as SKIPPED with that reason, so it shows up in every report and is never mistaken
    for a pass. It does not log in or open any page when skipped.

What it needs when turned on (a seed, made by hand per profile)
    A released SDM study on that profile, as CRDCDH-3026 TC201 needs a released
    automation_CompletedStudy. Create a study, create an SDM submission for it, upload valid SDM
    metadata, validate, submit and release it, then put the study's name in SDM_STUDY below.
    With the flag on and the seed missing the test FAILS with a message, it does not skip.
    Nothing is created or changed by this test; it only reads Data Explorer.

Flow (Submitter):
  1. Guard: SDM_STUDY must be filled in (fails if the seed name has not been set)
  2. Open Data Explorer and read the Data Commons filter options; SDM must be one of them
  3. Choose SDM in the Data Commons filter and wait for the list to reload
  4. The list has rows, and the Data Commons cell of every row includes SDM
  5. The seed study is listed
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.data_explorer_list import DataExplorerListPage

log = logging.getLogger("crdc_pw.tc_crdcdh_4027_data_explorer")

SDM = "SDM"

# Set to True once a released SDM study exists on the profile under test and SDM_STUDY is filled in.
RUN_SDM_DATA_EXPLORER_TEST = False

# Name of the released SDM study (the seed). Empty until someone creates and releases one. The
# Study Name column of the list is compared with it. Document who owns the seed when it is set.
SDM_STUDY = ""

pytestmark = pytest.mark.CRDC_Auxiliary


@pytest.mark.skipif(
    not RUN_SDM_DATA_EXPLORER_TEST,
    reason="RUN_SDM_DATA_EXPLORER_TEST is False: no released SDM study exists yet (SDM uploads fail in the Hub)",
)
@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC_CRDCDH_4027_SdmInDataExplorer(hub: Hub) -> None:
    explorer = DataExplorerListPage(hub)

    # 1. Guard: without the seed name the last step could not check anything.
    assert SDM_STUDY, "RUN_SDM_DATA_EXPLORER_TEST is on but SDM_STUDY is empty. Set the released SDM study name."

    # 2. Open Data Explorer and read the Data Commons filter. It lists only data commons that
    #    have released study data, so SDM missing here means no SDM study has been released on
    #    this profile (or the release has not reached Data Explorer yet).
    explorer.open()
    options = explorer.read_data_commons_options()
    assert SDM in options, f"No released SDM study: Data Commons filter offers {options}, not {SDM}. Seed is missing."

    # 3. Choose SDM in the filter. The list reloads to only the studies of that data commons.
    explorer.apply_data_commons_filter(SDM)

    # 4. Every row must name SDM in its Data Commons cell. A study can belong to several data
    #    commons, shown as a comma-separated list (for example "GC, SDM"), so split before
    #    comparing. The column is looked up by its header text, not by position.
    headers = explorer.read_table_headers()
    assert "Data Commons" in headers, f"No Data Commons column in {headers}"
    commons_column = headers.index("Data Commons")
    rows = explorer.read_table_rows()
    assert rows, "No rows in Data Explorer after filtering by SDM"
    for row in rows:
        commons = [name.strip() for name in row[commons_column].split(",")]
        assert SDM in commons, f"Row {row} is listed under SDM but its Data Commons is {commons}"

    # 5. The released seed study is one of the rows. The Study Name column is looked up by header.
    assert "Study Name" in headers, f"No Study Name column in {headers}"
    name_column = headers.index("Study Name")
    names = [row[name_column] for row in rows]
    assert SDM_STUDY in names, f"Seed study {SDM_STUDY!r} not in the SDM rows {names}"

    log.info(
        "PASS CRDCDH-4027 Data Explorer: %s rows under SDM incl. %r on profile=%s",
        len(rows),
        SDM_STUDY,
        hub.settings.profile,
    )
