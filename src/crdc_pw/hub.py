"""Logged-in Hub session the pytest fixture yields. Tests build page objects from this."""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page

from crdc_pw.config import Settings
from crdc_pw.locators.loader import LocatorLoader


@dataclass
class Hub:
    """One Chromium tab, already on Hub as role. No domain helpers — construct pages in the test."""

    page: Page
    locators: LocatorLoader
    settings: Settings
    role: str
