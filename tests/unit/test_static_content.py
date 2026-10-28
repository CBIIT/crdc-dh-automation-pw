"""No-browser checks for CMS notes markdown helpers (CRDCDH-3979).

Does not hit GitHub or Hub. Fetch stays unwired until the qa branch exists.

Flow (this file):
  1. Frontmatter block is dropped; body without --- is unchanged
  2. First heading or bullet is the snippet
  3. Empty body raises
  4. Raw URL uses the tier branch
"""

from __future__ import annotations

import pytest

from crdc_pw.utils.static_content import (
    NOTES_FILE,
    REPO,
    first_stable_heading_or_bullet,
    raw_notes_url,
    strip_yaml_frontmatter,
)


@pytest.mark.unit
def test_strip_yaml_frontmatter_drops_leading_block() -> None:
    raw = "---\ntitle: Release Notes\n---\n\n# 3.7.0\n- a fix\n"
    assert strip_yaml_frontmatter(raw) == "# 3.7.0\n- a fix\n"


@pytest.mark.unit
def test_strip_yaml_frontmatter_leaves_body_without_block() -> None:
    raw = "# 3.7.0\n- a fix\n"
    assert strip_yaml_frontmatter(raw) == raw


@pytest.mark.unit
def test_strip_yaml_frontmatter_keeps_unclosed_opening() -> None:
    raw = "---\ntitle: still open\n# 3.7.0\n"
    assert strip_yaml_frontmatter(raw) == raw


@pytest.mark.unit
def test_first_stable_heading() -> None:
    body = "\n# 3.7.0 (Released 10/22/2026)\n\n- a fix\n"
    assert first_stable_heading_or_bullet(body) == "3.7.0 (Released 10/22/2026)"


@pytest.mark.unit
def test_first_stable_bullet_when_no_heading() -> None:
    body = "- Previously approved forms can be reopened.\n"
    assert (
        first_stable_heading_or_bullet(body)
        == "Previously approved forms can be reopened."
    )


@pytest.mark.unit
def test_first_stable_heading_raises_when_empty() -> None:
    with pytest.raises(ValueError, match="no heading or bullet"):
        first_stable_heading_or_bullet("\n\n---\n")


@pytest.mark.unit
def test_raw_notes_url_uses_tier_branch() -> None:
    url = raw_notes_url("qa")
    assert url.startswith("https://raw.githubusercontent.com/")
    assert REPO in url
    assert "/qa/" in url
    assert url.endswith(NOTES_FILE)
