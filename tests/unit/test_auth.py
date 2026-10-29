"""No-browser checks for Login.gov role matching (switch_user vs SSO reuse).

NIH SSO can restore the previous Hub user after Logout. switch_user must not
treat 'already on Hub' as success unless the header is that role's PBAC name.

Flow (this file):
  1. Admin / Fedlead header names match their roles
  2. Admin header does not match Fedlead (the TC01 failure)
  3. Empty / unrelated names do not match
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crdc_pw.auth import storage_state_path, username_matches_role
from crdc_pw.config import Settings
from crdc_pw.locators.loader import repo_root


@pytest.mark.unit
def test_admin_header_matches_admin() -> None:
    """Hub header after Admin login (from live TC01)."""
    assert username_matches_role("PBAC.ADMIN-AUTOMATION", "Admin")


@pytest.mark.unit
def test_fedlead_display_name_matches_fedlead() -> None:
    """Manage Users / Profile style name still contains the pbac token."""
    assert username_matches_role(
        "Please Do Not Edit, pbac.fedlead-automation", "Fedlead"
    )


@pytest.mark.unit
def test_admin_header_does_not_match_fedlead() -> None:
    """SSO reuse of Admin must not count as a Fedlead login."""
    assert not username_matches_role("PBAC.ADMIN-AUTOMATION", "Fedlead")


@pytest.mark.unit
def test_empty_or_other_name_does_not_match() -> None:
    """Missing header or a different account is not a match."""
    assert not username_matches_role("", "Admin")
    assert not username_matches_role("PBAC.SUBMITTER-AUTOMATION", "Admin")


@pytest.mark.unit
def test_storage_state_path_uses_profile_and_role() -> None:
    """Saved sessions live under auth/<profile>/<Role>.json next to the lock file."""
    settings = Settings(profile="qa", base_url="https://example.invalid/", config_path=Path("unused"))
    assert storage_state_path(settings, "Admin") == repo_root() / "auth" / "qa" / "Admin.json"
