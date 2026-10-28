"""CRDC Data Hub Playwright test framework (Katalon port).

Layers:
  tests  ->  pages (header, login, studies, programs)  ->  YAML locators
  fixture  ->  auth (Login.gov OTP)  ->  Hub (page, locators, settings, role)
  utils  ->  non-page oracles (Excel, GitHub raw, TOTP)
"""

from crdc_pw.config import Settings, load_settings
from crdc_pw.locators.loader import LocatorLoader

__all__ = ["Settings", "load_settings", "LocatorLoader"]
