"""No-browser checks for profile YAML (qa / qa2 / stage URLs and role keys).

Katalon stored Hub URL + Login.gov accounts in Profiles/CRDC_QA.glbl (and QA2, STAGE).
This repo does the same in config/<profile>.yaml. These tests use committed
*.yaml.example files (or a temp yaml) — no real passwords.

Flow (this file):
  1. Default qa URL
  2. qa2 and stage URLs
  3. Example files have every role key (so CI unit jobs work on a fresh clone)
  4. Unknown role name raises
  5. Credentials come from yaml, not leftover env vars
  6. Missing qa.yaml falls back to qa.yaml.example
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from crdc_pw.config import ROLES, load_settings, profile_paths
from crdc_pw.locators.loader import repo_root


@pytest.mark.unit
def test_qa_profile_base_url() -> None:
    """load_settings(profile='qa') points at Hub QA."""
    settings = load_settings(profile="qa")
    assert settings.profile == "qa"
    assert settings.base_url == "https://hub-qa.datacommons.cancer.gov/"


@pytest.mark.unit
def test_qa2_and_stage_urls() -> None:
    """CRDC_PROFILE=qa2 / stage must not silently keep using QA."""
    assert load_settings(profile="qa2").base_url.endswith("hub-qa2.datacommons.cancer.gov/")
    assert load_settings(profile="stage").base_url.endswith("hub-stage.datacommons.cancer.gov/")


@pytest.mark.unit
def test_example_files_are_committed() -> None:
    """GitHub Actions unit jobs only have *.yaml.example in the checkout.

    Each example must list Email / Password / Secret keys for all six roles
    (values may be blank).
    """
    root = repo_root()
    for name in ("qa", "qa2", "stage"):
        _dest, example = profile_paths(root, name)
        assert example.is_file(), example
        with example.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        assert data["base_url"]
        for role in ROLES:
            assert f"{role}Email" in data
            assert f"{role}Password" in data
            assert f"{role}Secret" in data


@pytest.mark.unit
def test_unknown_role_raises() -> None:
    """settings.role() only accepts Admin, Fedlead, Dcp, Submitter, User, Master."""
    settings = load_settings(profile="qa")
    with pytest.raises(KeyError, match="Unknown role"):
        settings.role("Nope")


@pytest.mark.unit
def test_role_reads_yaml_not_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A leftover AdminEmail env var must not override the yaml (Katalon-style one-file profile)."""
    monkeypatch.delenv("AdminEmail", raising=False)
    dest = tmp_path / "config"
    dest.mkdir()
    (dest / "qa.yaml").write_text(
        "name: qa\n"
        "base_url: https://hub-qa.datacommons.cancer.gov/\n"
        "AdminEmail: admin@example.gov\n"
        "AdminPassword: secret-pass\n"
        "AdminSecret: TOTPSEED\n",
        encoding="utf-8",
    )
    settings = load_settings(profile="qa", root=tmp_path)
    creds = settings.role("Admin")
    assert creds.email == "admin@example.gov"
    assert creds.password == "secret-pass"
    assert creds.secret == "TOTPSEED"
    assert creds.is_complete()
    # Roles omitted from the yaml are blank, not an error (smoke skips them).
    assert not settings.role("Submitter").is_complete()


@pytest.mark.unit
def test_falls_back_to_example_when_yaml_missing(tmp_path: Path) -> None:
    """Fresh clone / Actions unit job: no gitignored qa.yaml, still load URL from the example."""
    dest = tmp_path / "config"
    dest.mkdir()
    (dest / "qa.yaml.example").write_text(
        "name: qa\nbase_url: https://hub-qa.datacommons.cancer.gov/\n",
        encoding="utf-8",
    )
    settings = load_settings(profile="qa", root=tmp_path)
    assert settings.config_path.name == "qa.yaml.example"
    assert settings.base_url.endswith("/")
