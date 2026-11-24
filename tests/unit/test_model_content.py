"""No-browser checks for the Hub model manifest helpers (CRDCDH-3921 / CRDCDH-4027).

Does not hit GitHub or Hub in unit tests.

Flow (this file):
  1. Raw URL uses the tier branch
  2. Visible names follow order, skip hidden models, use display-name or the key
  3. Models without a finite order come after ordered ones, in file order
  4. Hidden names and current version are read from the same entries
  5. Header menu text adds " Model" unless the name already has it
"""

from __future__ import annotations

import pytest

from crdc_pw.utils.model_content import (
    content_url,
    current_version,
    hidden_display_names,
    navigator_menu_label,
    visible_display_names,
)

# Shape of cache/content.json on the qa branch (trimmed).
SAMPLE = {
    "CDS": {"display-name": "GC", "order": 1, "current-version": "13.0.1"},
    "CCDI": {"display-name": "CCDI", "order": 2, "isHidden": True, "current-version": "3.1.0"},
    "CTDC": {"display-name": "CTDC", "order": 3, "current-version": "4.4.0"},
    "PSDC": {"display-name": "PSDC", "order": 5, "current-version": "2.0.0"},
    "SDM": {"display-name": "SDM", "order": 6, "current-version": "0.0.3"},
    "Hidden Model": {"display-name": "Hidden Model", "order": 99, "isHidden": True},
}


@pytest.mark.unit
def test_content_url_uses_tier_branch() -> None:
    """The profile name is the git branch in the raw URL."""
    assert content_url("qa2") == ("https://raw.githubusercontent.com/CBIIT/crdc-datahub-models/qa2/cache/content.json")


@pytest.mark.unit
def test_visible_display_names_follow_order_and_skip_hidden() -> None:
    """Hidden models are dropped; display-name replaces the key (CDS shows as GC); SDM is last."""
    assert visible_display_names(SAMPLE) == ["GC", "CTDC", "PSDC", "SDM"]


@pytest.mark.unit
def test_visible_display_names_sort_by_order_not_file_order() -> None:
    """A model listed first in the file but with a larger order comes later."""
    content = {"B": {"order": 2}, "A": {"order": 1}}
    assert visible_display_names(content) == ["A", "B"]


@pytest.mark.unit
def test_models_without_finite_order_come_after_ordered_ones_in_file_order() -> None:
    """Missing, non-numeric and non-finite orders all count as unordered and keep file order."""
    content = {
        "Z": {},
        "Y": {"order": "3"},
        "X": {"order": float("inf")},
        "W": {"order": 2},
        "V": {"order": True},
    }
    assert visible_display_names(content) == ["W", "Z", "Y", "X", "V"]


@pytest.mark.unit
def test_blank_display_name_falls_back_to_key() -> None:
    """A blank or missing display-name shows the manifest key; surrounding spaces are trimmed."""
    content = {"One": {"display-name": "   "}, "Two": {"display-name": " Dos "}, "Three": {}}
    assert visible_display_names(content) == ["One", "Dos", "Three"]


@pytest.mark.unit
def test_non_object_entries_are_skipped() -> None:
    """Entries that are not objects are ignored, as the frontend logs and skips them."""
    content = {"Good": {"order": 1}, "Bad": "text", "Worse": None}
    assert visible_display_names(content) == ["Good"]


@pytest.mark.unit
def test_hidden_display_names_lists_only_hidden_models() -> None:
    """isHidden must be exactly true; the list keeps manifest order."""
    content = {**SAMPLE, "Maybe": {"isHidden": "true", "order": 7}}
    assert hidden_display_names(content) == ["CCDI", "Hidden Model"]
    assert "Maybe" in visible_display_names(content)


@pytest.mark.unit
def test_navigator_menu_label_adds_model_unless_present() -> None:
    """The header menu says 'SDM Model', but leaves a name that already has Model alone."""
    assert navigator_menu_label("SDM") == "SDM Model"
    assert navigator_menu_label("GC") == "GC Model"
    assert navigator_menu_label("Hidden Model") == "Hidden Model"


@pytest.mark.unit
def test_current_version_by_key_or_display_name() -> None:
    """Look a model up by handle or by what the Hub shows."""
    assert current_version(SAMPLE, "SDM") == "0.0.3"
    assert current_version(SAMPLE, "GC") == "13.0.1"
    assert current_version(SAMPLE, "CDS") == "13.0.1"


@pytest.mark.unit
def test_current_version_raises_for_unknown_or_unversioned_model() -> None:
    """A model that is missing or has no current-version is an error, not an empty string."""
    with pytest.raises(KeyError):
        current_version(SAMPLE, "NOPE")
    with pytest.raises(KeyError):
        current_version(SAMPLE, "Hidden Model")
