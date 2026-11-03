"""GitHub raw markdown for CMS-managed Hub copy (CRDCDH-3979).

ReleaseNotesPage only reads Hub DOM. This module is the content oracle: GET
the published file on CBIIT/crdc-datahub-static-content, drop YAML frontmatter,
and pick normalized lines from the first release section the Hub page should contain.

Hub profile qa / qa2 / stage maps to the same git branch name on
CBIIT/crdc-datahub-static-content (file under content/).
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request

log = logging.getLogger("crdc_pw.utils.static_content")

# Hub release notes innerText can be very long; logs show a prefix only.
HUB_TEXT_LOG_PREVIEW = 400
_MATCH_CONTEXT_CHARS = 60
# Lines from the first ## block (until the next ##) to assert as substrings in Hub text.
ORACLE_MAX_LINES = 5

REPO = "CBIIT/crdc-datahub-static-content"
NOTES_FILE = "content/release-notes.md"
RAW_HOST = "https://raw.githubusercontent.com"


def raw_notes_url(branch: str) -> str:
    """Build the raw.githubusercontent.com URL for the notes file on a tier branch.

    branch is the Hub profile name (qa, qa2, stage). That is also the git branch
    static-content uses to publish each env.
    """
    return f"{RAW_HOST}/{REPO}/{branch}/{NOTES_FILE}"


def strip_yaml_frontmatter(raw: str) -> str:
    """Drop a leading --- yaml --- block so Hub-rendered text can be compared to the body.

    CMS files often start with YAML between two --- lines (title, date). Hub hides
    that block. If there is no opening ---, or no closing ---, return the text as-is
    so we do not swallow a whole file that is not frontmatter.
    """
    stripped = raw.lstrip()
    if not stripped.startswith("---"):
        return stripped
    # Skip the opening --- plus the newline after it.
    rest = stripped[3:].lstrip("\r\n")
    closer = "\n---"
    end = rest.find(closer)
    if end < 0:
        # Opening fence without a close: treat as not frontmatter.
        return stripped
    return rest[end + len(closer) :].lstrip()


def _oracle_line_from_markdown(line: str) -> str | None:
    """Map one markdown source line to plain text Hub should contain, or skip."""
    stripped = line.strip()
    if not stripped or stripped == "---":
        return None
    if stripped.startswith("#"):
        title = stripped.lstrip("#").strip()
        if title.lower() == "release notes":
            return None
        return title
    if stripped[0] in "-*":
        return stripped[1:].lstrip("\t ").strip() or None
    dot = stripped.find(".")
    if dot > 0 and stripped[:dot].isdigit():
        return stripped[dot + 1 :].strip() or None
    return None


def published_notes_oracle_lines(
    body: str,
    max_lines: int = ORACLE_MAX_LINES,
) -> list[str]:
    """Normalized lines from the first ## section (version block) for Hub substring checks.

    Stops at the next ## (next release) or max_lines. Skips # Release Notes before the
    first ##. Hub innerText will not match markdown syntax; each line is checked with ``in``.
    """
    oracles: list[str] = []
    in_first_section = False
    for raw_line in body.splitlines():
        if len(oracles) >= max_lines:
            break
        stripped = raw_line.strip()
        is_h2 = stripped.startswith("##") and not stripped.startswith("###")
        if is_h2:
            if in_first_section:
                break
            in_first_section = True
        if not in_first_section:
            continue
        parsed = _oracle_line_from_markdown(raw_line)
        if parsed:
            oracles.append(parsed)
    if not oracles:
        for raw_line in body.splitlines():
            parsed = _oracle_line_from_markdown(raw_line)
            if parsed:
                return [parsed]
        raise ValueError("static-content markdown had no oracle lines in first ## section")
    return oracles


def first_stable_heading_or_bullet(body: str) -> str:
    """Return the first oracle line (first ## section). Kept for small unit tests."""
    return published_notes_oracle_lines(body, max_lines=1)[0]


def fetch_raw_notes(branch: str, timeout_s: int = 30) -> str:
    """HTTP GET of the published markdown on branch.

    Uses stdlib urllib (no extra HTTP client). A missing branch or NOTES_FILE
    path comes back as HTTPError; rewrite that as URLError with the URL so the
    test log shows what we asked for.
    """
    url = raw_notes_url(branch)
    log.info("Fetch static-content notes: %s", url)
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise urllib.error.URLError(
            f"static-content notes not reachable ({exc.code}) at {url}"
        ) from exc


def published_notes_oracle_lines_for_branch(
    branch: str,
    timeout_s: int = 30,
    max_lines: int = ORACLE_MAX_LINES,
) -> list[str]:
    """Fetch tier markdown and return oracle lines for Hub parity checks."""
    raw = fetch_raw_notes(branch, timeout_s=timeout_s)
    return published_notes_oracle_lines(strip_yaml_frontmatter(raw), max_lines=max_lines)


def published_notes_snippet(branch: str, timeout_s: int = 30) -> str:
    """First oracle line only (legacy helper)."""
    return published_notes_oracle_lines_for_branch(branch, timeout_s=timeout_s, max_lines=1)[0]


def _text_preview(text: str, max_chars: int = HUB_TEXT_LOG_PREVIEW) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}…"


def assert_hub_notes_match_static_content(
    hub_text: str,
    branch: str,
    timeout_s: int = 30,
) -> None:
    """Assert Hub rendered notes include the GitHub oracle for this tier; log expected vs actual.

    hub_text is ReleaseNotesPage.markdown_text(). branch is the Hub profile (qa, qa2, …).
    Logs the GitHub URL, expected lines, Hub length/preview, and match context on success.
    """
    preview = _text_preview(hub_text)
    log.info(
        "Release Notes Hub actual: length=%s preview=%r",
        len(hub_text),
        preview,
    )
    oracle_url = raw_notes_url(branch)
    expected_lines = published_notes_oracle_lines_for_branch(branch, timeout_s=timeout_s)
    log.info(
        "Release Notes GitHub expected (branch=%s url=%s %s lines): %r",
        branch,
        oracle_url,
        len(expected_lines),
        expected_lines,
    )
    missing = [line for line in expected_lines if line not in hub_text]
    if missing:
        raise AssertionError(
            f"Hub notes do not match static-content branch {branch!r} ({oracle_url}); "
            f"missing {len(missing)}/{len(expected_lines)} oracle line(s): {missing!r}; "
            f"expected all of {expected_lines!r}; Hub preview: {preview!r}"
        )
    first = expected_lines[0]
    match_at = hub_text.find(first)
    start = max(0, match_at - _MATCH_CONTEXT_CHARS)
    end = min(len(hub_text), match_at + len(first) + _MATCH_CONTEXT_CHARS)
    log.info(
        "Release Notes CMS parity OK: %s/%s oracle lines found; first %r at index %s; context: %r",
        len(expected_lines),
        len(expected_lines),
        first,
        match_at,
        hub_text[start:end],
    )


def assert_rendered_notes_hide_frontmatter(hub_text: str) -> None:
    """Assert Hub did not render raw YAML frontmatter from the markdown source."""
    if hub_text.strip().startswith("---"):
        raise AssertionError("Release Notes showed raw YAML frontmatter")
    if "title:" in hub_text[:200].lower():
        raise AssertionError("Release Notes showed YAML title in body")
    log.info("Release Notes: no YAML frontmatter in rendered text")
