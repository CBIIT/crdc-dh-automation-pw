"""Hub Model Navigator (route /model-navigator/<model>/<version>).

Tests construct ModelNavigatorPage(hub) after HeaderPage.open_model_navigator_for(model), then:
  title                       — the page heading (for example "SDM Data Model")
  download(item, group=None)  — Available Downloads menu: open it, expand the group, click the
                                item, save the file and return its path

The page only saves and returns the file. The test decides what name, size or contents are right.
"""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.sync_api import Locator

from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.base import BasePage

log = logging.getLogger("crdc_pw.model_navigator")

_TITLE = "CRDC/AILocators/ModelNavigator/Title"
_DOWNLOADS_BTN = "CRDC/AILocators/ModelNavigator/Downloads-Btn"
_MENU_ITEM = "CRDC/AILocators/ModelNavigator/Downloads-MenuItem"

_DOWNLOAD_DIR = repo_root() / "test-results" / "downloads"
_DOWNLOAD_MS = 60_000


class ModelNavigatorPage(BasePage):
    @property
    def title(self) -> Locator:
        """Page heading. It is the only h2 and shows the model's page title."""
        return self._loc(_TITLE)

    def _menu_item(self, label: str) -> Locator:
        """Row of the open downloads menu for a label such as 'All Properties (PDF)'.

        A row can be split into a name and a second line ('All Vocabularies' and '(TSV)'), so
        match the name and the bracketed part separately.
        """
        name, _, rest = label.partition(" (")
        row = self._loc(_MENU_ITEM).filter(has_text=name)
        if rest:
            row = row.filter(has_text=rest.rstrip(")"))
        return row.first

    def download(self, item: str, group: str | None = None) -> Path:
        """Download one file from Available Downloads and return where it was saved.

        group is the expandable heading the item sits under (Data Dictionary, Submission
        Templates). Leave it None for items directly in the menu (All Vocabularies (TSV)).
        The file is saved under test-results/downloads with the name the Hub suggested.
        """
        self._loc(_DOWNLOADS_BTN).click()
        if group:
            self._menu_item(group).click()
        _DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with self.page.expect_download(timeout=_DOWNLOAD_MS) as download_info:
            self._menu_item(item).click()
        download = download_info.value
        destination = _DOWNLOAD_DIR / download.suggested_filename
        download.save_as(destination)
        # Close the menu so the next download opens it fresh instead of toggling it shut.
        self.page.keyboard.press("Escape")
        log.info("Model Navigator download %r: %s (%s bytes)", item, destination.name, destination.stat().st_size)
        return destination
