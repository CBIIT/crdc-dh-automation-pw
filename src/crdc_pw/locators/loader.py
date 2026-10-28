"""Load YAML locators (converted from Katalon .rs object-repository files).

Lookup is the same path Katalon used, for example:
    locators.get("CRDC/Login/Login.gov_UserEmail-TxtBx")

A locator's identity is folder + key, not the key alone — 43 leaf names repeat
in different folders. Pages call get(path) only.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Katalon parameterized objects used ${role}; the proposal also allows {role}.
_PLACEHOLDER_BRACES = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_PLACEHOLDER_KATALON = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_.]*)\}")


def repo_root() -> Path:
    """Project root (the folder that contains locators/, config/, tests/)."""
    # this file is src/crdc_pw/locators/loader.py -> four parents up
    return Path(__file__).resolve().parents[3]


def default_locators_dir() -> Path:
    """Root of the converted YAML object repository (locators/CRDC/...)."""
    return repo_root() / "locators"


class LocatorLoader:
    """Loads locators/*.yaml into an in-memory index keyed by Katalon path."""

    def __init__(self, locators_dir: Path | None = None) -> None:
        self.locators_dir = Path(locators_dir) if locators_dir else default_locators_dir()
        if not self.locators_dir.is_dir():
            raise FileNotFoundError(f"Locators directory not found: {self.locators_dir}")
        self._index: dict[str, str] = {}
        self._yaml_files: list[Path] = []
        self._load()

    @property
    def yaml_file_count(self) -> int:
        return len(self._yaml_files)

    @property
    def locator_count(self) -> int:
        return len(self._index)

    def get(self, path: str, **placeholders: Any) -> str:
        """Return the XPath for a Katalon-style path. Pass role='Admin' to fill ${role}."""
        xpath = self._index.get(path)
        if xpath is None:
            raise KeyError(f"Locator not found: {path}")
        return self._fill(xpath, placeholders)

    def has(self, path: str) -> bool:
        """True if this Katalon-style path was loaded from YAML."""
        return path in self._index

    def paths(self) -> list[str]:
        """All loaded paths, sorted. Used by unit tests to check catalog size."""
        return sorted(self._index)

    def _load(self) -> None:
        for yaml_path in sorted(self.locators_dir.rglob("*.yaml")):
            self._yaml_files.append(yaml_path)
            rel = yaml_path.relative_to(self.locators_dir)
            # Desktop.yaml lives in .../Header/Desktop/, so the folder is the Katalon path prefix.
            folder = str(rel.parent).replace("\\", "/")
            with yaml_path.open(encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            if not isinstance(data, dict):
                raise ValueError(f"Expected a mapping in {yaml_path}")
            self._ingest(folder, data)

    def _ingest(self, folder: str, data: dict[str, Any]) -> None:
        """Register each YAML key as folder/key. Nested mappings become more folders."""
        for key, value in data.items():
            nested = f"{folder}/{key}" if folder not in ("", ".") else str(key)
            if isinstance(value, dict):
                self._ingest(nested, value)
                continue
            if value is None:
                continue
            if nested in self._index:
                raise ValueError(f"Duplicate locator path: {nested}")
            self._index[nested] = str(value)

    @staticmethod
    def _fill(xpath: str, placeholders: dict[str, Any]) -> str:
        """Replace ${name} and {name} with kwargs. Fail if any placeholder is still there."""
        if not placeholders:
            return xpath
        filled = xpath
        for name, value in placeholders.items():
            text = str(value)
            filled = filled.replace(f"${{{name}}}", text)
            filled = filled.replace("{" + name + "}", text)
        leftover = _PLACEHOLDER_KATALON.findall(filled) + list(_PLACEHOLDER_BRACES.findall(filled))
        if leftover:
            raise KeyError(f"Locator has unfilled placeholders {leftover}: {filled}")
        return filled
