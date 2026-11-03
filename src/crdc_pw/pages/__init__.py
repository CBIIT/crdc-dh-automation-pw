"""Page objects: one Hub screen each. Tests construct these with PageClass(hub)."""

from crdc_pw.pages.header import HeaderPage
from crdc_pw.pages.login import LoginPage
from crdc_pw.pages.programs import ProgramsListPage
from crdc_pw.pages.release_notes import ReleaseNotesPage
from crdc_pw.pages.studies import StudiesListPage
from crdc_pw.pages.submission_request_form import SubmissionRequestFormPage
from crdc_pw.pages.submission_request import SubmissionRequest
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage
from crdc_pw.pages.users import ManageUsersPage, UserProfilePage

__all__ = [
    "HeaderPage",
    "LoginPage",
    "ManageUsersPage",
    "ProgramsListPage",
    "ReleaseNotesPage",
    "StudiesListPage",
    "SubmissionRequest",
    "SubmissionRequestFormPage",
    "SubmissionRequestsListPage",
    "UserProfilePage",
]
