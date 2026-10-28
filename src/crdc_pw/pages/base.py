"""Shared helper so every page can resolve a Katalon path to a Playwright locator."""

from __future__ import annotations

from playwright.sync_api import Locator, Page

from crdc_pw.locators.loader import LocatorLoader


class BasePage:
    """Every screen page inherits this so _loc('CRDC/...') resolves YAML → Playwright locator.

    Tests should not call _loc. Expose named locator properties on the page instead
    (studies.container, notes.markdown).
    """

    def __init__(self, page: Page, locators: LocatorLoader) -> None:
        self.page = page
        self.locators = locators

    def _loc(self, path: str, **placeholders: str) -> Locator:
        """Playwright locator for a YAML XPath. Pages only; tests use page properties."""
        return self.page.locator(self.locators.get(path, **placeholders))
