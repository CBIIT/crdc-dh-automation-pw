"""Shared helper so every page can resolve a Katalon path to a Playwright locator."""

from __future__ import annotations

from playwright.sync_api import Locator, Page

from crdc_pw.locators.loader import LocatorLoader


class BasePage:
    """Every screen page inherits this so loc('CRDC/...') resolves YAML → Playwright locator."""

    def __init__(self, page: Page, locators: LocatorLoader) -> None:
        self.page = page
        self.locators = locators

    def loc(self, path: str, **placeholders: str) -> Locator:
        """Playwright locator for a YAML XPath. Example: loc('CRDC/Login/Login.gov-Btn')."""
        return self.page.locator(self.locators.get(path, **placeholders))
