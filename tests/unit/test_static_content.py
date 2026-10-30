"""No-browser checks for CMS notes markdown helpers (CRDCDH-3979).

Does not hit GitHub or Hub in unit tests.

Flow (this file):
  1. Frontmatter block is dropped; body without --- is unchanged
  2. Oracle lines from first ## section (max 5)
  3. Empty body raises
  4. Raw URL uses the tier branch
"""

from __future__ import annotations

import pytest

from crdc_pw.utils.static_content import (
    NOTES_FILE,
    REPO,
    assert_rendered_notes_hide_frontmatter,
    first_stable_heading_or_bullet,
    published_notes_oracle_lines,
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
def test_first_stable_prefers_section_over_page_title() -> None:
    body = "# Release Notes\n\n## 3.7.1 (Released XX/XX/2026)\n"
    assert first_stable_heading_or_bullet(body) == "3.7.1 (Released XX/XX/2026)"


@pytest.mark.unit
def test_published_notes_oracle_lines_first_section_cap() -> None:
    body = (
        "# Release Notes\n\n"
        "## 3.7.1 (Released XX/XX/2026)\n\n"
        "### Submission request\n"
        "1. Test1\n"
        "2. Test 2\n"
        "3. Test 3\n\n"
        "### Data Submission\n"
        "- Hello\n\n"
        "## 3.7.0 (Released 10/22/2026)\n"
        "- old release\n"
    )
    assert published_notes_oracle_lines(body) == [
        "3.7.1 (Released XX/XX/2026)",
        "Submission request",
        "Test1",
        "Test 2",
        "Test 3",
    ]


@pytest.mark.unit
def test_first_stable_bullet_when_no_heading() -> None:
    body = "- Previously approved forms can be reopened.\n"
    assert (
        first_stable_heading_or_bullet(body)
        == "Previously approved forms can be reopened."
    )


@pytest.mark.unit
def test_first_stable_heading_raises_when_empty() -> None:
    with pytest.raises(ValueError, match="no oracle lines"):
        first_stable_heading_or_bullet("\n\n---\n")


@pytest.mark.unit
def test_raw_notes_url_uses_tier_branch() -> None:
    url = raw_notes_url("qa")
    assert url.startswith("https://raw.githubusercontent.com/")
    assert REPO in url
    assert "/qa/" in url
    assert url.endswith(NOTES_FILE)


@pytest.mark.unit
def test_assert_rendered_notes_hide_frontmatter_passes() -> None:
    assert_rendered_notes_hide_frontmatter("# Release Notes\n\n## 3.7.0\n")


@pytest.mark.unit
def test_assert_rendered_notes_hide_frontmatter_rejects_yaml() -> None:
    with pytest.raises(AssertionError, match="frontmatter"):
        assert_rendered_notes_hide_frontmatter("---\ntitle: x\n---\nbody")
