"""CRDC Data Hub Playwright test framework (Katalon port).

Layers:
  tests  ->  keywords (login, later PBAC)  ->  pages (header, login)  ->  YAML locators
"""

from crdc_pw.config import Settings, load_settings
from crdc_pw.locators.loader import LocatorLoader

__all__ = ["Settings", "load_settings", "LocatorLoader"]
