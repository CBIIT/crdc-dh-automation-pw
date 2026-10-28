"""No-browser checks for the GitHub Actions yaml writer.

CI cannot commit config/qa.yaml (secrets). The smoke job copies
qa.yaml.example to qa.yaml and overlays GitHub Environment secrets via
ci/write_profile_yaml.py → write_profile_yaml().

Flow (this file):
  1. Example + env overlay produces a filled qa.yaml that load_settings can use
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from crdc_pw.config import load_settings, write_profile_yaml


@pytest.mark.unit
def test_write_profile_overlays_secrets(tmp_path: Path) -> None:
    """Blank Admin* keys in the example are replaced by env values; other keys stay."""
    dest = tmp_path / "config"
    dest.mkdir()
    (dest / "qa.yaml.example").write_text(
        "name: qa\n"
        "base_url: https://hub-qa.datacommons.cancer.gov/\n"
        "AdminEmail:\n"
        "AdminPassword:\n"
        "AdminSecret:\n",
        encoding="utf-8",
    )
    written = write_profile_yaml(
        tmp_path,
        {
            "CRDC_PROFILE": "qa",
            "AdminEmail": "admin@example.gov",
            "AdminPassword": "secret-pass",
            "AdminSecret": "TOTPSEED",
        },
    )
    assert written == dest / "qa.yaml"
    with written.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert data["AdminEmail"] == "admin@example.gov"
    settings = load_settings(profile="qa", root=tmp_path)
    assert settings.role("Admin").is_complete()
    assert settings.config_path.name == "qa.yaml"
