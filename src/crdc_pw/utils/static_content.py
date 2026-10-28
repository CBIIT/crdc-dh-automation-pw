"""GitHub raw markdown for CMS-managed Hub copy (CRDCDH-3979).

ReleaseNotesPage only reads Hub DOM. This module is the content oracle: GET
the published file on CBIIT/crdc-datahub-static-content, drop YAML frontmatter,
and pick one heading or bullet the page should contain.

Hub profile qa / qa2 / stage maps to the same git branch name. Fill NOTES_FILE
when 3979 lands (path on that branch). Live tests must not call fetch until
the qa branch exists and the repo is reachable without extra auth.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request

log = logging.getLogger("crdc_pw.utils.static_content")

REPO = "CBIIT/crdc-datahub-static-content"
# Path inside the repo. Update when 3979 publishes the notes file.
NOTES_FILE = "release-notes.md"
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


def first_stable_heading_or_bullet(body: str) -> str:
    """Return the first heading or list item from the markdown body.

    Hub inner text will not match the raw file 1:1 (lists, whitespace). One
    heading or bullet is enough to prove Hub is serving this file. Skip blank
    lines and leftover --- so a stray fence is not used as the snippet.
    """
    for line in body.splitlines():
        line = line.strip()
        if not line or line == "---":
            continue
        if line.startswith("#"):
            return line.lstrip("#").strip()
        if line.startswith(("- ", "* ")):
            return line[2:].strip()
    raise ValueError("static-content markdown had no heading or bullet")


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


def published_notes_snippet(branch: str, timeout_s: int = 30) -> str:
    """Fetch, strip frontmatter, and return one heading or bullet from that file.

    This is what the live test should call later: assert the snippet is in
    ReleaseNotesPage.markdown_text(). Does not open Hub.
    """
    raw = fetch_raw_notes(branch, timeout_s=timeout_s)
    return first_stable_heading_or_bullet(strip_yaml_frontmatter(raw))
