"""Read excel_ds_validation settings from profile YAML (optional block)."""

from __future__ import annotations

import os
from typing import Any

from crdc_pw.config import Settings

_DEFAULT_GLOB = "tests/DataValidation/**/*.xlsx"
_ENV_ENABLE = "CRDC_EXCEL_DS_VALIDATION"


def _excel_block(settings: Settings) -> dict[str, Any]:
    raw = settings.data.get("excel_ds_validation")
    if isinstance(raw, dict):
        return raw
    return {}


def excel_ds_enabled(settings: Settings) -> bool:
    """True when excel_ds_validation.enabled is true or CRDC_EXCEL_DS_VALIDATION=1."""
    env = os.environ.get(_ENV_ENABLE, "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    block = _excel_block(settings)
    enabled = block.get("enabled")
    if enabled is True:
        return True
    if enabled is False or enabled is None:
        return False
    return str(enabled).strip().lower() in ("true", "yes", "y", "1")


def excel_ds_cases_glob(settings: Settings) -> str:
    """Glob relative to repo root for Excel test case workbooks (documentation / tooling)."""
    block = _excel_block(settings)
    for key in ("excel_cases_glob", "scenarios_glob"):
        value = block.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return _DEFAULT_GLOB


def excel_ds_scenarios_glob(settings: Settings) -> str:
    """Deprecated alias for excel_ds_cases_glob."""
    return excel_ds_cases_glob(settings)
