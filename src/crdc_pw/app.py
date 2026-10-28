"""Bundle the browser page, locators, and keywords that a test uses.

The `app` pytest fixture builds one of these per test (and per role for smoke).
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page

from crdc_pw.config import Settings
from crdc_pw.keywords.login import LoginKeywords
from crdc_pw.keywords.programs import ManageProgramsKeywords
from crdc_pw.keywords.studies import ManageStudiesKeywords
from crdc_pw.locators.loader import LocatorLoader
from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.login import LoginPage


@dataclass
class App:
    """Logged-in Hub session a test receives. Scenario uses header / studies / programs; login_otp already ran."""

    page: Page  # Playwright tab
    locators: LocatorLoader  # loaded YAML locators (Katalon findTestObject)
    config: Settings  # profile URL + role credentials
    login: LoginKeywords
    header: HeaderPage
    login_page: LoginPage
    studies: ManageStudiesKeywords
    programs: ManageProgramsKeywords
    role: str = "Admin"  # which PBAC account this browser is using
