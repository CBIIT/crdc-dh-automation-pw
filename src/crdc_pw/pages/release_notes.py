"""Hub Release Notes screen (public /release-notes).

Tests construct this from hub (ReleaseNotesPage(hub.page, hub.locators)), then:
  open()           — footer System Info → Release Notes, wait for markdown or error
  markdown_text()  — rendered markdown inner text

YAML paths stay on this page. Tests use notes.markdown / notes.error.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Locator

from crdc_pw.pages.base import BasePage

log = logging.getLogger("crdc_pw.release_notes")

_FOOTER = "CRDC/AILocators/Global/Footer/DesktopFooter"
_FOOTER_LINK = "CRDC/AILocators/Global/Footer/ReleaseNotes-Link"
_MARKDOWN = "CRDC/AILocators/ReleaseNotes/MarkdownContent"
_ERROR = "CRDC/AILocators/ReleaseNotes/ErrorAlert"


class ReleaseNotesPage(BasePage):
    @property
    def markdown(self) -> Locator:
        return self._loc(_MARKDOWN)

    @property
    def error(self) -> Locator:
        return self._loc(_ERROR)

    def open(self) -> None:
        """Scroll the desktop footer into view, click Release Notes, wait until markdown or error shows."""
        log.info("Navigate: Release Notes")
        footer = self._loc(_FOOTER)
        footer.scroll_into_view_if_needed()
        link = self._loc(_FOOTER_LINK)
        link.wait_for(state="visible", timeout=self.RELEASE_NOTES_MS)
        link.click()
        # Hub uses client-side routing on some envs (e.g. QA2): URL and content update
        # without a new document "load", so wait_for_url(..., wait_until="load") can time
        # out while the page is already correct. Readiness = markdown or error visible.
        self.wait_until_ready()
        log.info("Release Notes page loaded")

    def wait_until_ready(self) -> None:
        """Block until the markdown body or the error alert is on screen (GitHub fetch can be slow)."""
        self.markdown.or_(self.error).first.wait_for(state="visible", timeout=self.RELEASE_NOTES_MS)

    def markdown_text(self) -> str:
        """Inner text of the rendered markdown. Empty string if the node is not there yet."""
        return (self.markdown.inner_text() or "").strip()
