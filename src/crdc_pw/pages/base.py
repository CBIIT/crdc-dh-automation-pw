"""Shared helper so every page can resolve a Katalon path to a Playwright locator.

Also holds Hub timeouts and widget helpers list pages share (table wait/read,
MUI dropdown, snackbar). Pages own YAML paths and named filters; tests do not
call these methods.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import NamedTuple

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crdc_pw.hub import Hub
from crdc_pw.locators.loader import LocatorLoader
from crdc_pw.utils.table_helpers import (
    DisplayedRows,
    expected_page_count,
    expected_page_range,
    is_sorted,
    parse_displayed_rows,
)

log = logging.getLogger("crdc_pw.table")

_POLL_MS = 150

# Shared by DS list, SR list, Manage Users/Programs/Studies, Data Explorer, VR table, etc.
_GENERIC_TABLE_LOADING_ROW = "CRDC/AILocators/GenericTable/LoadingRow"
_GENERIC_TABLE_ROW = "CRDC/AILocators/GenericTable/TableRow"
_GENERIC_TABLE_HEADER = "CRDC/AILocators/GenericTable/HeaderCell"
_ROWS_PER_PAGE = "CRDC/AILocators/GenericTable/Pagination/RowsPerPage-Ddn"
_DISPLAYED_ROWS = "CRDC/AILocators/GenericTable/Pagination/DisplayedRows-Lbl"
_NEXT_PAGE = "CRDC/AILocators/GenericTable/Pagination/NextPage-Btn"
_PREVIOUS_PAGE = "CRDC/AILocators/GenericTable/Pagination/PreviousPage-Btn"
_CURRENT_PAGE = "CRDC/AILocators/GenericTable/Pagination/CurrentPage-Btn"
_GO_TO_PAGE = "CRDC/AILocators/GenericTable/Pagination/GoToPage-Btn"
_PAGE_BUTTONS = "CRDC/AILocators/GenericTable/Pagination/PaginationNav-Buttons"

# One JS pass over every header cell: name, whether it has a sort control, and the active
# direction. The table has no aria-sort, so direction comes from the MUI TableSortLabel classes.
_HEADER_STATES_JS = """
headers => headers.map(h => {
    const label = h.querySelector('.MuiTableSortLabel-root');
    const text = (h.innerText || '').replace(/\\s+/g, ' ').trim();
    const name = text || (h.getAttribute('data-testid') || '').replace('generic-table-header-', '');
    if (!label) return {name, sortable: false, direction: null};
    const labelClass = label.getAttribute('class') || '';
    if (!labelClass.includes('Mui-active')) return {name, sortable: true, direction: null};
    const icon = label.querySelector('.MuiTableSortLabel-icon');
    const iconClass = icon ? (icon.getAttribute('class') || '') : '';
    if (iconClass.includes('MuiTableSortLabel-iconDirectionAsc')) return {name, sortable: true, direction: 'asc'};
    if (iconClass.includes('MuiTableSortLabel-iconDirectionDesc')) return {name, sortable: true, direction: 'desc'};
    if (labelClass.includes('MuiTableSortLabel-directionAsc')) return {name, sortable: true, direction: 'asc'};
    if (labelClass.includes('MuiTableSortLabel-directionDesc')) return {name, sortable: true, direction: 'desc'};
    return {name, sortable: true, direction: null};
})
"""


class ColumnSort(NamedTuple):
    """One table column header: its name, whether it can be sorted, and the active direction."""

    name: str
    sortable: bool
    direction: str | None

# One JS pass per read (Katalon readGenericTableRowsViaJs): truncated cells expose the full
# text on the wrapper aria-label, while innerText shows "auto-test_...".
_READ_ROWS_JS = """
rows => rows.map(row => Array.from(row.querySelectorAll('td')).map(cell => {
    const trunc = cell.querySelector("[data-testid='truncated-text-wrapper']");
    if (trunc) {
        const aria = trunc.getAttribute('aria-label');
        if (aria && aria.trim()) return aria.trim();
    }
    return (cell.innerText || '').trim();
}))
"""


class BasePage:
    """Hub-backed screen page: _loc('CRDC/...') always uses the live tab on hub.

    Tests construct pages with PageClass(hub) after login. LoginPage is the exception
    (auth bootstrap uses page + locators directly).

    DEFAULT_MS is the Hub action/expect timeout (wired on the browser context).
    PROBE_MS is for optional chrome (banner, is the username there yet).
    RELEASE_NOTES_MS is the GitHub-fetch wait on /release-notes.
    """

    DEFAULT_MS = 15_000
    PROBE_MS = 2_000
    RELEASE_NOTES_MS = 30_000

    def __init__(self, hub: Hub) -> None:
        self._hub = hub

    @property
    def page(self) -> Page:
        return self._hub.page

    @property
    def locators(self) -> LocatorLoader:
        return self._hub.locators

    def _loc(self, path: str, **placeholders: str) -> Locator:
        """Playwright locator for a YAML XPath. Pages only; tests use page properties."""
        return self.page.locator(self.locators.get(path, **placeholders))

    def _table_fingerprint(self, rows: Locator) -> str:
        """Joined inner text of every current data row. Empty string if none."""
        return "\n".join(text.strip() for text in rows.all_inner_texts())

    def wait_for_generic_table_settled(
        self,
        rows: Locator | None = None,
        *,
        previous: str | None = None,
        loading_path: str = _GENERIC_TABLE_LOADING_ROW,
    ) -> None:
        """Wait for the Hub generic-table loading row, then optional row refresh (fingerprint).

        Pass ``rows`` (and optionally ``previous``) when a filter/refetch should complete.
        Omit ``rows`` to wait only for the loading skeleton (e.g. initial list open).

        Override ``loading_path`` only if a screen uses a non-standard loading indicator.
        """
        self._wait_for_table_settled(self._loc(loading_path), rows, previous=previous)

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

    def _read_table_rows_full_text(self, rows: Locator) -> list[list[str]]:
        """Each data row as td text, using the truncated-text aria-label when a cell is truncated.

        One JS pass (no stale handles across re-renders). Empty list if there are no rows.
        """
        result: list[list[str]] = rows.evaluate_all(_READ_ROWS_JS)
        return result

    def _read_table_headers(self, table: Locator) -> list[str]:
        """Column header text in order, whitespace collapsed (look cells up by name)."""
        texts = table.first.locator("xpath=.//thead//th").all_inner_texts()
        return [" ".join(text.split()) for text in texts]

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

    # ------------------------------------------------------------------
    # Generic table: sorting and pagination (list pages call these with expected
    # data from the test; every verify_* raises one AssertionError listing all problems)
    # ------------------------------------------------------------------

    def _poll_until(self, condition: Callable[[], bool], timeout_ms: int | None = None) -> bool:
        """Poll condition until it is true or the timeout (Hub default) passes. Return its last value."""
        deadline = time.monotonic() + (timeout_ms or self.DEFAULT_MS) / 1000
        while time.monotonic() < deadline:
            if condition():
                return True
            self.page.wait_for_timeout(_POLL_MS)
        return condition()

    @staticmethod
    def _fail_if(problems: list[str], what: str) -> None:
        if problems:
            raise AssertionError(f"{what}: " + "; ".join(problems))

    def read_column_sort_states(self) -> list[ColumnSort]:
        """Name, sortable flag and active direction of every column header, in order."""
        raw: list[dict[str, object]] = self._loc(_GENERIC_TABLE_HEADER).evaluate_all(_HEADER_STATES_JS)
        return [ColumnSort(str(h["name"]), bool(h["sortable"]), h["direction"]) for h in raw]  # type: ignore[arg-type]

    def _column_index(self, column: str) -> int:
        """Index of the header whose text equals column (case-insensitive). Raise if missing."""
        names = [state.name for state in self.read_column_sort_states()]
        for index, name in enumerate(names):
            if name.lower() == column.strip().lower():
                return index
        raise AssertionError(f"Column {column!r} not found; headers are {names}")

    def read_column_values(self, column: str) -> list[str]:
        """Cell text of one column for the rows on the current page ("" for a short row)."""
        index = self._column_index(column)
        rows = self._read_table_rows_full_text(self._loc(_GENERIC_TABLE_ROW))
        return [row[index] if index < len(row) else "" for row in rows]

    def click_column_sort(self, column: str) -> str | None:
        """Click the column's sort control, wait for the direction and data to settle.

        Returns the direction now shown on that column (None if it never became active).
        Waits on the header direction, not on row text, so two sorts that give the same
        first page do not cost a full timeout.
        """
        index = self._column_index(column)
        before = self.read_column_sort_states()[index].direction
        header = self._loc(_GENERIC_TABLE_HEADER).nth(index)
        header.locator("css=.MuiTableSortLabel-root").first.click()
        self._poll_until(lambda: self.read_column_sort_states()[index].direction != before)
        self.wait_for_generic_table_settled()
        return self.read_column_sort_states()[index].direction

    def verify_column_sortability(self, non_sortable: list[str]) -> None:
        """Every column is sortable except those whose name contains a non_sortable entry."""
        skip = [name.lower() for name in non_sortable]
        problems: list[str] = []
        states = self.read_column_sort_states()
        if not states:
            raise AssertionError("No table headers found")
        for state in states:
            expect_sortable = not any(name in state.name.lower() for name in skip)
            log.info("Column %r sortable=%s (expected %s)", state.name, state.sortable, expect_sortable)
            if state.sortable != expect_sortable:
                problems.append(
                    f"{state.name!r} sortable={state.sortable}, expected {expect_sortable}"
                )
        self._fail_if(problems, "Column sortability")

    def verify_default_sort(self, column: str, direction: str) -> None:
        """The table opens sorted by column in direction, and the rows are in that order."""
        states = self.read_column_sort_states()
        active = [s for s in states if s.direction]
        problems: list[str] = []
        if len(active) != 1:
            problems.append(f"expected exactly one sorted column, found {[(s.name, s.direction) for s in active]}")
        elif active[0].name.lower() != column.lower() or active[0].direction != direction:
            problems.append(
                f"default sort is {active[0].name!r} {active[0].direction}, expected {column!r} {direction}"
            )
        else:
            values = self.read_column_values(column)
            log.info("Default sort %s %s values: %s", column, direction, values)
            if not is_sorted(values, direction):
                problems.append(f"{column!r} rows are not in {direction} order: {values}")
        self._fail_if(problems, "Default sort")

    def verify_column_sort_on_click(self, column: str) -> None:
        """Clicking column sorts the data one way, and clicking again sorts it the other way."""
        problems: list[str] = []
        first = self.click_column_sort(column)
        log.info("%s first click direction: %s", column, first)
        if first is None:
            problems.append("first click did not activate sorting")
        else:
            values = self.read_column_values(column)
            if not is_sorted(values, first):
                problems.append(f"first click ({first}) rows not in order: {values}")
            expected = "desc" if first == "asc" else "asc"
            second = self.click_column_sort(column)
            log.info("%s second click direction: %s", column, second)
            if second != expected:
                problems.append(f"second click direction {second}, expected {expected}")
            else:
                values = self.read_column_values(column)
                if not is_sorted(values, second):
                    problems.append(f"second click ({second}) rows not in order: {values}")
        self._fail_if(problems, f"Sort on click for {column!r}")

    # --- pagination reads ---

    def read_rows_per_page_options(self) -> list[int]:
        """The numbers offered by the rows-per-page select, in order."""
        select = self._loc(_ROWS_PER_PAGE).first
        values: list[str] = select.locator("option").evaluate_all("opts => opts.map(o => o.value)")
        return [int(value) for value in values if value.strip().isdigit()]

    def read_rows_per_page(self) -> int:
        """The rows-per-page value currently selected."""
        return int(self._loc(_ROWS_PER_PAGE).first.input_value())

    def read_visible_row_count(self) -> int:
        """Number of data rows shown on the current page."""
        return self._loc(_GENERIC_TABLE_ROW).count()

    def read_displayed_rows(self) -> DisplayedRows | None:
        """The "from-to of total" label, parsed. None if missing or not in that format."""
        label = self._loc(_DISPLAYED_ROWS).first
        if label.count() == 0:
            return None
        return parse_displayed_rows(label.inner_text())

    def read_current_page(self) -> int | None:
        """The active page number. None if the pagination has no active page button."""
        current = self._loc(_CURRENT_PAGE).first
        if current.count() == 0:
            return None
        text = current.inner_text().strip()
        return int(text) if text.isdigit() else None

    def read_total_pages(self) -> int | None:
        """Highest page number among the pagination buttons. None if there are none."""
        texts = self._loc(_PAGE_BUTTONS).all_inner_texts()
        numbers = [int(text.strip()) for text in texts if text.strip().isdigit()]
        return max(numbers) if numbers else None

    def _page_button_enabled(self, path: str) -> bool | None:
        """True or False for an enabled or disabled button, None if it is not on the page."""
        button = self._loc(path).first
        if button.count() == 0:
            return None
        return button.is_enabled()

    # --- pagination actions ---

    def _page_rows_fingerprint(self) -> str:
        """Joined text of the data rows on the current page (compare before and after a page change)."""
        return self._table_fingerprint(self._loc(_GENERIC_TABLE_ROW))

    def _click_page_control(self, path: str, reached: Callable[[int | None], bool]) -> None:
        """Click a pagination control, wait until reached(current page) is true, then for new rows.

        Waits on the row text changing (up to the Hub default) so the next read is not of the
        old page. If the rows never change this returns anyway and the caller's check reports it.
        """
        previous = self._page_rows_fingerprint()
        self._loc(path).first.click()
        self._poll_until(lambda: reached(self.read_current_page()))
        self.wait_for_generic_table_settled(self._loc(_GENERIC_TABLE_ROW), previous=previous)

    def go_to_next_page(self) -> None:
        before = self.read_current_page()
        self._click_page_control(_NEXT_PAGE, lambda page: page != before)

    def go_to_previous_page(self) -> None:
        before = self.read_current_page()
        self._click_page_control(_PREVIOUS_PAGE, lambda page: page != before)

    def go_to_page(self, number: int) -> None:
        if self.read_current_page() == number:
            return
        previous = self._page_rows_fingerprint()
        self._loc(_GO_TO_PAGE, page=str(number)).first.click()
        self._poll_until(lambda: self.read_current_page() == number)
        self.wait_for_generic_table_settled(self._loc(_GENERIC_TABLE_ROW), previous=previous)

    def change_rows_per_page(self, count: int) -> None:
        """Pick count in the rows-per-page select and wait until the page shows that many rows."""
        self._loc(_ROWS_PER_PAGE).first.select_option(str(count))

        def _settled() -> bool:
            shown = self.read_displayed_rows()
            rows = self.read_visible_row_count()
            return (
                self.read_rows_per_page() == count
                and shown is not None
                and rows == min(count, shown.total)
                and shown.last - shown.first + 1 == rows
            )

        self._poll_until(_settled)
        self.wait_for_generic_table_settled()

    # --- pagination verifies ---

    def verify_rows_per_page_options(self, expected: list[int]) -> None:
        actual = self.read_rows_per_page_options()
        log.info("Rows-per-page options: %s", actual)
        self._fail_if(
            [] if actual == expected else [f"options {actual}, expected {expected}"],
            "Rows-per-page options",
        )

    def verify_default_rows_per_page(self, expected: int) -> None:
        actual = self.read_rows_per_page()
        log.info("Default rows per page: %s", actual)
        self._fail_if(
            [] if actual == expected else [f"default {actual}, expected {expected}"],
            "Default rows per page",
        )

    def verify_displayed_rows_text(self) -> None:
        """The "from-to of total" label is well formed and matches the rows on the page."""
        shown = self.read_displayed_rows()
        rows = self.read_visible_row_count()
        log.info("Displayed rows label: %s, visible rows: %s", shown, rows)
        problems: list[str] = []
        if shown is None:
            problems.append("label missing or not in 'from-to of total' format")
        else:
            if shown.first < 1 or shown.last < shown.first or shown.last > shown.total:
                problems.append(f"label numbers out of range: {shown}")
            if shown.last - shown.first + 1 != rows:
                problems.append(f"label covers {shown.last - shown.first + 1} rows but {rows} are shown")
        self._fail_if(problems, "Displayed rows text")

    def verify_page_navigation(self) -> None:
        """Previous and Next, page-number buttons and the first and last page edges all work."""
        problems: list[str] = []
        if self.read_current_page() not in (None, 1) and self._loc(_GO_TO_PAGE, page="1").count():
            self.go_to_page(1)
        if self.read_current_page() != 1:
            problems.append(f"table does not start on page 1 (current {self.read_current_page()})")
        if self._page_button_enabled(_PREVIOUS_PAGE) is not False:
            problems.append("Previous is not disabled on page 1")
        total = self.read_total_pages()
        shown = self.read_displayed_rows()
        page_size = self.read_rows_per_page()
        total_rows = shown.total if shown is not None else None
        if total_rows is not None:
            expected_total = expected_page_count(total_rows, page_size)
            if total != expected_total:
                problems.append(f"pagination ends at page {total}, expected {expected_total}")
        log.info("Total pages: %s", total)
        if total is None or total < 2:
            if self._page_button_enabled(_NEXT_PAGE) is not False:
                problems.append("single page, but Next is not disabled")
            self._fail_if(problems, "Page navigation")
            return

        # Every move also has to replace the rows on screen, not only the button and label.
        # Each step compares with the page just left (page 1 against page 2, and so on), never
        # page 1 against its earlier self, so a list that reorders mid-run does not fail this.
        rows_before = self._page_rows_fingerprint()
        self.go_to_next_page()
        if self.read_current_page() != 2:
            problems.append(f"Next from page 1 landed on {self.read_current_page()}, expected 2")
        self._expect_label_range(2, page_size, total_rows, problems)
        rows_before = self._expect_rows_replaced(rows_before, "Next to page 2", problems)

        self.go_to_previous_page()
        if self.read_current_page() != 1:
            problems.append(f"Previous from page 2 landed on {self.read_current_page()}, expected 1")
        self._expect_label_range(1, page_size, total_rows, problems)
        rows_before = self._expect_rows_replaced(rows_before, "Previous to page 1", problems)

        self.go_to_page(2)
        if self.read_current_page() != 2:
            problems.append(f"page button 2 landed on {self.read_current_page()}")
        self._expect_label_range(2, page_size, total_rows, problems)
        rows_before = self._expect_rows_replaced(rows_before, "page button 2", problems)

        # With exactly two pages the last page is the one already shown, so nothing changes.
        self.go_to_page(total)
        if self.read_current_page() != total:
            problems.append(f"last page button landed on {self.read_current_page()}, expected {total}")
        if total > 2:
            rows_before = self._expect_rows_replaced(rows_before, f"page button {total}", problems)
        if self._page_button_enabled(_NEXT_PAGE) is not False:
            problems.append("Next is not disabled on the last page")
        self._expect_label_range(total, page_size, total_rows, problems)

        self.go_to_page(1)
        if self.read_current_page() != 1:
            problems.append(f"could not return to page 1 (current {self.read_current_page()})")
        self._expect_label_range(1, page_size, total_rows, problems)
        self._expect_rows_replaced(rows_before, "page button 1", problems)
        self._fail_if(problems, "Page navigation")

    def _expect_label_range(
        self, page: int, page_size: int, total_rows: int | None, problems: list[str]
    ) -> None:
        """Add a problem unless the label shows both ends of page's slice, like 21-40 of 193.

        total_rows is the label total read on page 1 (None if the label was missing then).
        """
        shown = self.read_displayed_rows()
        if shown is None or total_rows is None:
            problems.append(f"page {page}: displayed-rows label missing ({shown})")
            return
        first, last = expected_page_range(page, page_size, total_rows)
        if (shown.first, shown.last, shown.total) != (first, last, total_rows):
            problems.append(
                f"page {page} label is {shown.first}-{shown.last} of {shown.total}, "
                f"expected {first}-{last} of {total_rows}"
            )

    def _expect_rows_replaced(self, before: str, what: str, problems: list[str]) -> str:
        """Add a problem if the rows on screen are still those of the page just left.

        Returns the rows now shown, to compare with after the next move.
        """
        now = self._page_rows_fingerprint()
        if now == before:
            problems.append(f"{what}: the table rows did not change")
        return now

    def verify_rows_per_page_change(self, count: int) -> None:
        """After choosing count: the select shows it, and the page shows 1 to count rows from row 1."""
        self.change_rows_per_page(count)
        selected = self.read_rows_per_page()
        rows = self.read_visible_row_count()
        shown = self.read_displayed_rows()
        log.info("Rows per page %s: select=%s rows=%s label=%s", count, selected, rows, shown)
        problems: list[str] = []
        if selected != count:
            problems.append(f"select shows {selected}, expected {count}")
        expected_rows = min(count, shown.total) if shown is not None else None
        if expected_rows is not None and rows != expected_rows:
            problems.append(f"{rows} rows shown, expected {expected_rows}")
        if shown is None:
            problems.append("displayed-rows label missing")
        elif shown.first != 1 or shown.last != rows:
            problems.append(f"label {shown} does not match {rows} rows starting at 1")
        self._fail_if(problems, f"Rows per page {count}")
