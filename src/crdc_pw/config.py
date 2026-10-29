"""Load Hub URL and Login.gov accounts from one YAML file per Katalon profile.

Katalon stored URL + secrets together in Profiles/CRDC_QA.glbl (and QA2, STAGE).
This repo does the same in config/qa.yaml, qa2.yaml, and stage.yaml.

Those files are gitignored (they contain passwords and TOTP seeds).
Committed copies are config/*.yaml.example (URL filled, secrets blank).

Which file to load: CRDC_PROFILE=qa|qa2|stage (shell env, not a .env file).
If the real yaml is missing (fresh clone, GitHub Actions unit job), the
matching .example is used so URL checks still run. Smoke still needs a
filled yaml — locally you copy the example; in Actions the workflow writes
the file from GitHub Environment secrets (see ci/write_profile_yaml.py).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from crdc_pw.locators.loader import repo_root

# Same six accounts as Katalon TC18_LoginAllRolesAndSwitchUser.
ROLES = ("Admin", "Fedlead", "Dcp", "Submitter", "User", "Master")
PROFILES = ("qa", "qa2", "stage")


@dataclass(frozen=True)
class RoleCredentials:
    """One Login.gov user. secret is the TOTP seed (Katalon *Secret)."""

    role: str
    email: str
    password: str
    secret: str

    def is_complete(self) -> bool:
        """True when email, password, and TOTP secret are all non-empty (smoke can log in)."""
        return bool(self.email and self.password and self.secret)


@dataclass(frozen=True)
class Settings:
    profile: str  # qa, qa2, or stage
    base_url: str
    config_path: Path
    data: dict[str, Any] = field(default_factory=dict)

    def role(self, name: str) -> RoleCredentials:
        """Read AdminEmail / AdminPassword / AdminSecret (and the other roles) from the YAML."""
        key = name.strip()
        if key not in ROLES:
            raise KeyError(f"Unknown role '{name}'. Expected one of: {', '.join(ROLES)}")
        return RoleCredentials(
            role=key,
            email=_yaml_str(self.data, f"{key}Email"),
            password=_yaml_str(self.data, f"{key}Password"),
            secret=_yaml_str(self.data, f"{key}Secret"),
        )


def _yaml_str(data: dict[str, Any], key: str) -> str:
    """YAML value as stripped text. Missing keys become '' so role() does not KeyError."""
    value = data.get(key)
    if value is None:
        return ""
    return str(value).strip()


def profile_paths(root: Path | None, profile: str) -> tuple[Path, Path]:
    """Return (real yaml, committed example) for a profile name."""
    base = (root or repo_root()) / "config"
    return base / f"{profile}.yaml", base / f"{profile}.yaml.example"


def write_profile_yaml(root: Path, environ: dict[str, str] | None = None) -> Path:
    """Copy config/<profile>.yaml.example to the gitignored yaml, overlaying env values.

    GitHub Actions uses this after checkout (see ci/write_profile_yaml.py).
    Prints how many roles were filled. Never prints secret values.
    """
    env = environ if environ is not None else os.environ
    name = (env.get("CRDC_PROFILE") or "qa").strip().lower()
    if name not in PROFILES:
        raise ValueError(f"Unknown profile '{name}'. Expected one of: {', '.join(PROFILES)}")
    dest, example = profile_paths(root, name)
    if not example.is_file():
        raise FileNotFoundError(f"Missing example profile: {example}")
    with example.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{example} must be a YAML mapping")

    base_url = (env.get("BASE_URL") or env.get("G_Urlname") or "").strip()
    if base_url:
        data["base_url"] = base_url

    filled = 0
    for role in ROLES:
        for suffix in ("Email", "Password", "Secret"):
            key = f"{role}{suffix}"
            value = env.get(key)
            if value is None:
                continue
            data[key] = value
        if data.get(f"{role}Email") and data.get(f"{role}Password") and data.get(f"{role}Secret"):
            filled += 1

    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, default_flow_style=False, sort_keys=False)
    try:
        shown = dest.relative_to(root)
    except ValueError:
        shown = dest
    print(f"Wrote {shown} with {filled}/{len(ROLES)} complete roles")
    return dest


def load_settings(profile: str | None = None, root: Path | None = None) -> Settings:
    """Pick a profile (CRDC_PROFILE or the argument) and load that YAML.

    Prefers config/<profile>.yaml. Falls back to the committed .example when
    the real file is absent (unit tests on a fresh clone / GitHub Actions).
    """
    base = root or repo_root()
    name = (profile or os.environ.get("CRDC_PROFILE") or "qa").strip().lower()
    if name not in PROFILES:
        raise ValueError(f"Unknown profile '{name}'. Expected one of: {', '.join(PROFILES)}")
    config_path, example_path = profile_paths(base, name)
    # Prefer the gitignored yaml (secrets). Fall back to the committed example
    # so unit tests run on a fresh clone without copying qa.yaml.
    if config_path.is_file():
        path = config_path
    elif example_path.is_file():
        path = example_path
    else:
        raise FileNotFoundError(
            f"Profile config not found: {config_path} (or {example_path})"
        )
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config '{path}' must be a YAML mapping")
    base_url = _yaml_str(data, "base_url")
    if not base_url:
        raise ValueError(f"config '{path}' is missing base_url")
    # Trailing slash so callers can join paths the same way every time.
    return Settings(
        profile=name,
        base_url=base_url.rstrip("/") + "/",
        config_path=path,
        data=data,
    )
