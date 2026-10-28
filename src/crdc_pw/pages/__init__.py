"""Page objects: thin wrappers that turn locator paths into clicks and fills."""

from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.login import LoginPage
from crdc_pw.pages.programs import ProgramsListPage
from crdc_pw.pages.studies import StudiesListPage

__all__ = ["HeaderPage", "LoginPage", "ProgramsListPage", "StudiesListPage"]
