"""No-browser checks that the converted YAML locators load and look up correctly.

These run without Hub or Chromium (`pytest tests/unit -m unit`). They catch a
broken catalog or a renamed Katalon path before a live smoke pays OTP.

Flow (this file):
  1. Catalog size matches the conversion report
  2. Paths used by login + TC08/TC09 + CRDCDH-3974 still resolve
  3. Missing path raises
  4. Placeholder substitution (Katalon ${role} and {role})
"""

from __future__ import annotations

import pytest

from crdc_pw.locators.loader import LocatorLoader


@pytest.mark.unit
def test_loader_loads_converted_yaml(locators: LocatorLoader) -> None:
    """Whole locators/CRDC tree loaded; counts come from locators/CONVERSION_REPORT.md."""
    # 91 YAML files / 721 locators from the Katalon conversion report.
    assert locators.yaml_file_count == 91
    assert locators.locator_count >= 700


@pytest.mark.unit
def test_login_and_header_paths_used_by_smoke(locators: LocatorLoader) -> None:
    """XPaths the live smoke (login, header, Manage Studies/Programs, Release Notes) actually clicks."""
    # Login.gov + system-use banner
    assert "user_email" in locators.get("CRDC/Login/Login.gov_UserEmail-TxtBx")
    assert locators.get("CRDC/Login/LoginPageLogin-Btn")
    assert locators.get("CRDC/AILocators/Home/LoginDialogLogin-Btn")
    assert locators.get("CRDC/Login/Login.gov-Btn")
    assert "system-use-warning-dialog" in locators.get(
        "CRDC/AILocators/Global/SystemUseWarning/Continue-Btn"
    )
    assert locators.get("CRDC/AILocators/Global/SystemUseWarning/Warning-Dialog")

    # Desktop header (username, Manage Studies / Programs)
    assert "navbar-dropdown-name" in locators.get(
        "CRDC/AILocators/Global/Header/Desktop/UserName-Btn"
    )
    assert locators.get("CRDC/AILocators/Global/Header/Desktop/ManageStudies-Link")
    assert locators.get("CRDC/AILocators/Global/Header/Desktop/ManagePrograms-Link")

    # TC08 Manage Studies list + filters (including dropdown option placeholders)
    assert locators.get("CRDC/AILocators/Studies/List/Container")
    assert locators.get("CRDC/AILocators/Studies/List/AddStudy-Btn")
    assert locators.get("CRDC/AILocators/GenericTable/TableRow")
    assert locators.get("CRDC/AILocators/Studies/List/Filters/StudyName-TxtBx")
    assert locators.get("CRDC/AILocators/Studies/List/Filters/Program-Ddn")
    assert locators.get("CRDC/AILocators/Studies/List/Filters/Status-Ddn")
    assert locators.get("CRDC/AILocators/Studies/List/Filters/AccessType-Ddn")
    program = locators.get(
        "CRDC/AILocators/Studies/List/Filters/Program-Option", program="AutoTest-Program"
    )
    assert "AutoTest-Program" in program
    status = locators.get(
        "CRDC/AILocators/Studies/List/Filters/Status-Option", status="Active"
    )
    assert "status-option-Active" in status

    # TC09 Manage Programs list + filters
    assert locators.get("CRDC/AILocators/Programs/List/Container")
    assert locators.get("CRDC/AILocators/Programs/List/AddProgram-Btn")
    assert locators.get("CRDC/AILocators/Programs/List/Filters/ProgramName-TxtBx")
    assert locators.get("CRDC/AILocators/Programs/List/Filters/StudyName-TxtBx")

    # CRDCDH-3974 Release Notes (footer link + page body)
    assert locators.get("CRDC/AILocators/Global/Footer/DesktopFooter")
    assert "/release-notes" in locators.get("CRDC/AILocators/Global/Footer/ReleaseNotes-Link")
    markdown = locators.get("CRDC/AILocators/ReleaseNotes/MarkdownContent")
    assert "release-notes-markdown" in markdown
    assert "Release Notes" in markdown
    assert "release-notes-error" in locators.get("CRDC/AILocators/ReleaseNotes/ErrorAlert")

    # TC01 Manage Users / Profile permission form
    assert locators.get("CRDC/AILocators/Global/Header/Desktop/ManageUsers-Link")
    assert locators.get("CRDC/AILocators/Global/Header/Desktop/UserProfile-Link")
    assert locators.get("CRDC/AILocators/Users/List/Container")
    assert locators.get("CRDC/AILocators/Users/List/UserFilter-TxtBx")
    assert locators.get("CRDC/AILocators/GenericTable/TableRow")
    assert locators.get("CRDC/ManageUsers/ManageUsersTable-Row")
    assert locators.get("CRDC/ManageUsers/PermissionsPanel-Ddn")
    assert locators.get("CRDC/ManageUsers/PbacOptions-Chkbx")
    assert locators.get("CRDC/AILocators/GenericTable/Pagination/NextPage-Btn")

    # TC08 GC metadata VR (create DS, upload, Validation Results)
    assert locators.get("CRDC/AILocators/Global/Header/Desktop/DataSubmissions-Tab")
    assert locators.get("CRDC/AILocators/DataSubmissions/List/Table/CreateDataSubmission-Btn")
    assert locators.get("CRDC/DataSubmissions/DataSubmissionName-Link")
    assert locators.get("CRDC/DataSubmissions/ChooseFiles-Btn")
    assert locators.get("CRDC/DataSubmissions/Validate-Btn")
    assert locators.get("CRDC/DataSubmissions/Validation/ValidationResults-Tab")
    assert locators.get("CRDC/DataSubmissions/Validation/Table-Row")


@pytest.mark.unit
def test_missing_path_raises(locators: LocatorLoader) -> None:
    """A typo in a page constant should fail here, not as a 15s Playwright timeout."""
    with pytest.raises(KeyError, match="Locator not found"):
        locators.get("CRDC/DoesNotExist/Missing-Btn")


@pytest.mark.unit
def test_katalon_placeholder_substitution(locators: LocatorLoader) -> None:
    """YAML still uses Katalon ${role}; loader must splice the value into the XPath."""
    xpath = locators.get("CRDC/ManageUsers/RoleDdn-Option", role="Admin")
    assert xpath == "//li[text()='Admin']"


@pytest.mark.unit
def test_brace_placeholder_substitution(locators: LocatorLoader) -> None:
    """Same path also accepts Python-style {role} kwargs."""
    xpath = locators.get("CRDC/ManageUsers/RoleDdn-Option", role="Submitter")
    assert "Submitter" in xpath
