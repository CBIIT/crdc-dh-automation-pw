"""Guards that every CRDC/ path in pages/ exists in the YAML loader (no browser).

A typo in a page constant fails here, not as a 15s live timeout. Existence
only: do not fill ${role} placeholders. Do not scan tests/ (intentional misses).

Flow:
  1. Collect quoted CRDC/... strings from src/crdc_pw/pages/*.py
  2. Each unique path is in LocatorLoader
"""

from __future__ import annotations

import re

import pytest

from crdc_pw.locators.loader import LocatorLoader, repo_root


pytestmark = pytest.mark.unit

# Letter after CRDC/ so docstring examples like _loc('CRDC/...') are not paths.
_PATH = re.compile(r"""['"](CRDC/[A-Za-z][^'"]+)['"]""")
_PAGES = repo_root() / "src" / "crdc_pw" / "pages"


def _page_locator_paths() -> list[str]:
    """Unique Katalon paths quoted in page modules, sorted for a stable failure list."""
    found: set[str] = set()
    for path in sorted(_PAGES.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        found.update(_PATH.findall(text))
    return sorted(found)


def test_pages_quote_at_least_one_crdc_path() -> None:
    """Scanner is looking at the page package, not an empty folder."""
    assert _page_locator_paths(), f"no CRDC/ strings under {_PAGES}"


def test_every_page_locator_path_exists(locators: LocatorLoader) -> None:
    """Each CRDC/... constant on a page is a loaded YAML path."""
    missing = [path for path in _page_locator_paths() if not locators.has(path)]
    assert missing == [], f"page locator paths not in YAML: {missing}"
