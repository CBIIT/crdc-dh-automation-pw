"""Xray CRDCDH-4006 / story CRDCDH-3974 — CMS-managed Release Notes.

Hub loads markdown from CBIIT/crdc-datahub-static-content on a git branch that
matches the run profile (qa2 → branch qa2, file content/release-notes.md). We
compare one stable line from that file to the text Playwright reads from the
page. We do not diff the whole file: rendered innerText drops markdown syntax
and spacing differs from the raw .md.

Flow:
  1. Open /release-notes via the desktop footer link
  2. Confirm the notes body rendered (not the fetch-error alert)
  3. Confirm the body has text
  4. Confirm a GitHub oracle substring appears in Hub text (CMS parity)
  5. Confirm YAML frontmatter from the .md file is not shown to the user
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.pages.release_notes import ReleaseNotesPage
from crdc_pw.utils.static_content import (
    assert_hub_notes_match_static_content,
    assert_rendered_notes_hide_frontmatter,
)

log = logging.getLogger("crdc_pw.tc_crdcdh_3974")

pytestmark = pytest.mark.CRDC_Auxiliary


def test_TC_CRDCDH_3974_ReleaseNotesPage(hub: Hub) -> None:
    notes = ReleaseNotesPage(hub.page, hub.locators)

    # 1. Navigate: scroll footer into view, click Release Notes, wait for content.
    notes.open()

    # 2. Verify UI state: CMS path shows markdown; a failed GitHub fetch shows the error alert.
    expect(notes.markdown).to_be_visible()
    expect(notes.error).not_to_be_visible()

    # 3. Verify the page has rendered copy (not an empty shell).
    text = notes.markdown_text()
    assert text, "Release Notes markdown was empty"

    # 4. Verify Hub matches static-content for this tier (logs expected GitHub vs actual Hub text).
    assert_hub_notes_match_static_content(text, hub.settings.profile)

    # 5. Verify frontmatter stripping: users must not see raw --- / title: from the .md source.
    assert_rendered_notes_hide_frontmatter(text)

    log.info("PASS CRDCDH-3974: Release Notes verified for profile=%s as %s", hub.settings.profile, hub.role)
