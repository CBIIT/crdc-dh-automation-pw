"""Shared helper so every page can resolve a Katalon path to a Playwright locator.

Also holds Hub timeouts and widget helpers list pages share (table wait/read,
MUI dropdown, snackbar). Pages own YAML paths and named filters; tests do not
call these methods.
"""

from __future__ import annotations

import time

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.locators.loader import LocatorLoader

_POLL_MS = 150


class BasePage:
    """Every screen page inherits this so _loc('CRDC/...') resolves YAML → Playwright locator.

    Tests should not call _loc. Expose named locator properties on the page instead
    (studies.container, notes.markdown).

    DEFAULT_MS is the Hub action/expect timeout (wired on the browser context).
    PROBE_MS is for optional chrome (banner, is the username there yet).
    RELEASE_NOTES_MS is the GitHub-fetch wait on /release-notes.
    """

    DEFAULT_MS = 15_000
    PROBE_MS = 2_000
    RELEASE_NOTES_MS = 30_000

    def __init__(self, page: Page, locators: LocatorLoader) -> None:
        self.page = page
        self.locators = locators

    def _loc(self, path: str, **placeholders: str) -> Locator:
        """Playwright locator for a YAML XPath. Pages only; tests use page properties."""
        return self.page.locator(self.locators.get(path, **placeholders))

    def _table_fingerprint(self, rows: Locator) -> str:
        """Joined inner text of every current data row. Empty string if none."""
        return "\n".join(text.strip() for text in rows.all_inner_texts())

    def _wait_for_table_settled(
        self,
        loading: Locator,
        rows: Locator | None = None,
        previous: str | None = None,
    ) -> None:
        """Wait out the spinner, then until row text changes if previous was given.

        The loading-row locator is hidden when it is not in the DOM. Waiting only
        for hidden therefore succeeds before a debounced spinner appears. Probe
        visible first, then hidden. previous None: spinner only (plain read after
        open). If row text never changes and the spinner is gone, return.
        """
        spinner = loading.first
        try:
            spinner.wait_for(state="visible", timeout=self.PROBE_MS)
        except PlaywrightTimeoutError:
            pass
        spinner.wait_for(state="hidden")
        if previous is None or rows is None:
            return
        deadline = time.monotonic() + self.DEFAULT_MS / 1000
        while self._table_fingerprint(rows) == previous:
            if time.monotonic() >= deadline:
                if spinner.is_visible():
                    raise PlaywrightTimeoutError("Table still loading after filter")
                return
            self.page.wait_for_timeout(_POLL_MS)

    def _read_table_rows(self, rows: Locator) -> list[list[str]]:
        """Each data row as a list of td text (header order). Empty list if none."""
        result: list[list[str]] = []
        for row in rows.all():
            result.append([text.strip() for text in row.locator("td").all_inner_texts()])
        return result

    def _select_dropdown(self, dropdown: Locator, option: Locator) -> None:
        """Click a MUI/select dropdown, then the option locator."""
        dropdown.first.click()
        option.first.click()

    def _wait_for_snackbar_gone(self, snackbar: Locator) -> None:
        """Probe for the snackbar, then wait until it is gone.

        If it never appears, return. Hidden after visible uses the Hub default.
        """
        try:
            snackbar.wait_for(state="visible", timeout=self.PROBE_MS)
        except PlaywrightTimeoutError:
            return
        snackbar.wait_for(state="hidden")

    @staticmethod
    def _trim(value: str | None) -> str | None:
        """None and blank/whitespace become None; otherwise the stripped string."""
        if value is None:
            return None
        text = value.strip()
        return text or None
