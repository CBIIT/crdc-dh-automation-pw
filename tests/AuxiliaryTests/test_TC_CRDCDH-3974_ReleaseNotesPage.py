"""Xray CRDCDH-4006 / story CRDCDH-3974 — CMS-managed Release Notes (scaffold).

`hub` is already signed in as Admin (fixture). This file is the scenario after login.

Flow:
  1. Open Release Notes from the desktop footer
  2. Assert the markdown body is visible and the error alert is not
  3. Assert the markdown text is non-empty

When CRDCDH-3979 ships and the static-content qa branch exists, extend this
case: page text matches a known string from that branch, and YAML frontmatter
is not shown. Do not pin a GitHub URL or version here — the source will change.
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import expect

from crdc_pw.hub import Hub
from crdc_pw.pages.release_notes import ReleaseNotesPage

log = logging.getLogger("crdc_pw.tc_crdcdh_3974")

pytestmark = pytest.mark.CRDC_Auxiliary


def test_TC_CRDCDH_3974_ReleaseNotesPage(hub: Hub) -> None:
    notes = ReleaseNotesPage(hub.page, hub.locators)

    # 1. Footer System Info → Release Notes
    notes.open()

    # 2. Markdown loaded; fetch-error alert is not shown
    expect(notes.markdown).to_be_visible()
    expect(notes.error).not_to_be_visible()
    log.info("Assert Release Notes: markdown visible, error alert hidden")

    # 3. Rendered notes are non-empty (do not pin version or source URL)
    text = notes.markdown_text()
    assert text, "Release Notes markdown was empty"
    log.info("Assert Release Notes: markdown text length=%s", len(text))

    # TODO(CRDCDH-3979): when static-content qa exists, extend this case:
    #   snippet = published_notes_snippet(hub.settings.profile)
    #   assert snippet in text, "Hub notes do not match static-content qa"
    #   assert not text.strip().startswith("---")
    #   assert "title:" not in text[:200]
    # Fill NOTES_FILE in crdc_pw.utils.static_content. Do not add a second test.

    log.info("PASS CRDCDH-3974: Release Notes page loaded as %s", hub.role)
