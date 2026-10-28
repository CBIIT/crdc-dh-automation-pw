"""Load YAML locators (converted from Katalon .rs object-repository files).

Lookup is the same path Katalon used, for example:
    locators.get("CRDC/Login/Login.gov_UserEmail-TxtBx")

A locator's identity is folder + key, not the key alone — 43 leaf names repeat
in different folders. Optional: locators.CRDC.Login.Login_gov_UserEmail_TxtBx
(hyphens and dots become underscores for Python attributes).
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


def _attr_name(key: str) -> str:
    """Save-Btn -> Save_Btn so it can be a Python attribute."""
    return key.replace("-", "_").replace(".", "_")


class LocatorNode:
    """One folder in the locator tree, or a leaf that holds an XPath."""

    def __init__(self, name: str = "") -> None:
        self._name = name
        self._children: dict[str, LocatorNode] = {}
        self._xpath: str | None = None

    def __getattr__(self, name: str) -> LocatorNode | str:
        if name.startswith("_"):
            raise AttributeError(name)
        child = self._children.get(name)
        if child is None:
            available = ", ".join(sorted(self._children)) or "(none)"
            raise AttributeError(
                f"No locator node '{name}' under '{self._name or 'locators'}'. Available: {available}"
            )
        # Leaf: return the XPath string. Folder: return the child node.
        if child._xpath is not None and not child._children:
            return child._xpath
        return child

    def __repr__(self) -> str:
        return f"LocatorNode({self._name!r})"


class LocatorLoader:
    """Loads locators/*.yaml into an in-memory index keyed by Katalon path."""

    def __init__(self, locators_dir: Path | None = None) -> None:
        self.locators_dir = Path(locators_dir) if locators_dir else default_locators_dir()
        if not self.locators_dir.is_dir():
            raise FileNotFoundError(f"Locators directory not found: {self.locators_dir}")
        self._index: dict[str, str] = {}
        self._yaml_files: list[Path] = []
        self._root = LocatorNode("locators")
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

    def __getattr__(self, name: str) -> LocatorNode | str:
        return getattr(self._root, name)

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
            self._ingest(folder, data, self._root)

    def _ingest(self, folder: str, data: dict[str, Any], node: LocatorNode) -> None:
        """Walk folder segments (CRDC/Login) so attribute access can follow the same tree."""
        folder_parts = [p for p in folder.split("/") if p and p != "."]
        current = node
        walked: list[str] = []
        for part in folder_parts:
            walked.append(part)
            attr = _attr_name(part)
            if attr not in current._children:
                current._children[attr] = LocatorNode("/".join(walked))
            current = current._children[attr]
        self._ingest_keys(folder, data, current)

    def _ingest_keys(self, folder: str, data: dict[str, Any], node: LocatorNode) -> None:
        """Register each YAML key as folder/key. Nested mappings become more folders."""
        for key, value in data.items():
            if isinstance(value, dict):
                nested_folder = f"{folder}/{key}" if folder not in ("", ".") else key
                attr = _attr_name(str(key))
                if attr not in node._children:
                    node._children[attr] = LocatorNode(nested_folder)
                self._ingest_keys(nested_folder, value, node._children[attr])
                continue
            if value is None:
                continue
            xpath = str(value)
            path = f"{folder}/{key}" if folder not in ("", ".") else str(key)
            if path in self._index:
                raise ValueError(f"Duplicate locator path: {path}")
            self._index[path] = xpath
            attr = _attr_name(str(key))
            # UserName-Btn and UserName.Btn would both become UserName_Btn.
            if attr in node._children and node._children[attr]._xpath is not None:
                raise ValueError(
                    f"Duplicate attribute '{attr}' under '{node._name}' "
                    f"(from keys that normalize to the same name)"
                )
            leaf = LocatorNode(path)
            leaf._xpath = xpath
            node._children[attr] = leaf

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
