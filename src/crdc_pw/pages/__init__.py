"""Page objects: one Hub screen each. Tests construct these from hub.page + hub.locators."""

from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.login import LoginPage
from crdc_pw.pages.programs import ProgramsListPage
from crdc_pw.pages.studies import StudiesListPage
from crdc_pw.pages.users import ManageUsersPage, UserProfilePage

__all__ = [
    "HeaderPage",
    "LoginPage",
    "ManageUsersPage",
    "ProgramsListPage",
    "StudiesListPage",
    "UserProfilePage",
]
