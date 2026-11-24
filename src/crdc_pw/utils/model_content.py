"""Hub data-model manifest: the oracle for which models the Hub shows (CRDCDH-3921).

The Hub reads cache/content.json from CBIIT/crdc-datahub-models on a git branch named after the
tier (dev, qa, qa2, stage, prod). The Create a Data Submission dialog, the Model Navigator header
menu and the user profile list the models from that file. Tests build their expected lists here
instead of hard coding which models exist.

Hub profile qa / qa2 / dev maps to the same branch name on crdc-datahub-models. The ordering and
hidden rules copy the frontend buildDataModels: a model with isHidden true is not shown, models
with a finite order come first (ascending), the rest keep file order, and the shown name is
display-name or, when blank, the manifest key.
"""

from __future__ import annotations

import json
import logging
import math
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger("crdc_pw.utils.model_content")

REPO = "CBIIT/crdc-datahub-models"
CONTENT_FILE = "cache/content.json"
RAW_HOST = "https://raw.githubusercontent.com"

ModelContent = dict[str, dict[str, Any]]


def content_url(tier: str) -> str:
    """Build the raw.githubusercontent.com URL of content.json on a tier branch.

    tier is the Hub profile name (dev, qa, qa2), which is also the branch name.
    """
    return f"{RAW_HOST}/{REPO}/{tier}/{CONTENT_FILE}"


def fetch_model_content(profile: str, timeout_s: int = 30) -> ModelContent:
    """HTTP GET of content.json for the profile's tier branch, parsed.

    A missing branch or file comes back as HTTPError; rewrite that as URLError with the URL so
    the test log shows what was asked for. Raises ValueError when the body is not a JSON object.
    """
    url = content_url(profile)
    log.info("Fetch model manifest: %s", url)
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise urllib.error.URLError(f"model manifest not reachable ({exc.code}) at {url}") from exc
    content = json.loads(body)
    if not isinstance(content, dict):
        raise ValueError(f"model manifest at {url} is not a JSON object")
    return content


def _entries(content: ModelContent) -> list[tuple[str, dict[str, Any]]]:
    """Manifest entries that are objects, in file order. Others are skipped like the frontend does."""
    return [(key, value) for key, value in content.items() if key and isinstance(value, dict)]


def _display_name(key: str, entry: dict[str, Any]) -> str:
    """display-name when it is a non-blank string, else the manifest key."""
    name = entry.get("display-name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return key


def _finite_order(entry: dict[str, Any]) -> float | None:
    """The numeric order, or None when it is missing, not a number or not finite."""
    order = entry.get("order")
    if isinstance(order, bool) or not isinstance(order, (int, float)):
        return None
    return float(order) if math.isfinite(order) else None


def _sorted_entries(content: ModelContent) -> list[tuple[str, dict[str, Any]]]:
    """Entries with a finite order first (ascending), then the rest in file order (stable sort)."""

    def sort_key(item: tuple[str, dict[str, Any]]) -> tuple[int, float]:
        order = _finite_order(item[1])
        return (0, order) if order is not None else (1, 0.0)

    return sorted(_entries(content), key=sort_key)


def visible_display_names(content: ModelContent) -> list[str]:
    """Display names of every model that is not hidden, in the order the Hub lists them."""
    return [_display_name(key, entry) for key, entry in _sorted_entries(content) if entry.get("isHidden") is not True]


def hidden_display_names(content: ModelContent) -> list[str]:
    """Display names of every model whose isHidden is true, in the same order."""
    return [_display_name(key, entry) for key, entry in _sorted_entries(content) if entry.get("isHidden") is True]


def navigator_menu_label(display_name: str) -> str:
    """Text of a model's item in the Model Navigator header menu.

    The Hub adds " Model" unless the display name already contains "Model", so GC shows as
    "GC Model" and a model named "SDM Data Model" would stay as it is.
    """
    return display_name if "Model" in display_name else f"{display_name} Model"


def current_version(content: ModelContent, model: str) -> str:
    """current-version of a model, found by manifest key or by display name.

    Raises KeyError when no entry matches or the entry has no current-version.
    """
    for key, entry in _entries(content):
        if model in (key, _display_name(key, entry)):
            version = entry.get("current-version")
            if isinstance(version, str) and version:
                return version
            raise KeyError(f"model {model!r} has no current-version in the manifest")
    raise KeyError(f"model {model!r} is not in the manifest")
