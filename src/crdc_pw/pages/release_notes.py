"""Hub Release Notes screen (public /release-notes).

Tests construct this from hub (ReleaseNotesPage(hub.page, hub.locators)), then:
  open()           — footer System Info → Release Notes, wait for markdown or error
  markdown_text()  — rendered markdown inner text

Locator constants are Katalon object-repository paths (YAML), not raw XPath.
"""

from __future__ import annotations

import logging

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.pages.base import BasePage

log = logging.getLogger("crdc_pw.release_notes")

FOOTER = "CRDC/AILocators/Global/Footer/DesktopFooter"
FOOTER_LINK = "CRDC/AILocators/Global/Footer/ReleaseNotes-Link"
MARKDOWN = "CRDC/AILocators/ReleaseNotes/MarkdownContent"
ERROR = "CRDC/AILocators/ReleaseNotes/ErrorAlert"


class ReleaseNotesPage(BasePage):
    def open(self, timeout_ms: int = 30000) -> None:
        """Scroll the desktop footer into view, click Release Notes, wait until markdown or error shows."""
        log.info("Navigate: Release Notes")
        footer = self.loc(FOOTER)
        footer.scroll_into_view_if_needed()
        link = self.loc(FOOTER_LINK)
        link.wait_for(state="visible", timeout=timeout_ms)
        link.click()
        self.page.wait_for_url("**/release-notes", timeout=timeout_ms)
        self.wait_until_ready(timeout_ms=timeout_ms)
        log.info("Release Notes page loaded")

    def wait_until_ready(self, timeout_ms: int = 30000) -> None:
        """Block until the markdown body or the error alert is on screen (GitHub fetch can be slow)."""
        markdown = self.loc(MARKDOWN)
        error = self.loc(ERROR)
        try:
            markdown.or_(error).first.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            log.info("Release Notes: neither markdown nor error visible within %sms", timeout_ms)
            raise

    def markdown_text(self) -> str:
        """Inner text of the rendered markdown. Empty string if the node is not there yet."""
        return (self.loc(MARKDOWN).inner_text() or "").strip()
