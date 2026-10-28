"""No-browser checks that the converted YAML locators load and look up correctly."""

from __future__ import annotations

import pytest

from crdc_pw.locators.loader import LocatorLoader


@pytest.mark.unit
def test_loader_loads_converted_yaml(locators: LocatorLoader) -> None:
    # 91 YAML files / 721 locators from the Katalon conversion report.
    assert locators.yaml_file_count == 91
    assert locators.locator_count >= 700


@pytest.mark.unit
def test_login_and_header_paths_used_by_smoke(locators: LocatorLoader) -> None:
    assert "user_email" in locators.get("CRDC/Login/Login.gov_UserEmail-TxtBx")
    assert locators.get("CRDC/Login/LoginPageLogin-Btn")
    assert locators.get("CRDC/Login/Login.gov-Btn")
    assert "system-use-warning-dialog" in locators.get(
        "CRDC/AILocators/Global/SystemUseWarning/Continue-Btn"
    )
    assert "navbar-dropdown-name" in locators.get(
        "CRDC/AILocators/Global/Header/Desktop/UserName-Btn"
    )
    assert locators.get("CRDC/AILocators/Global/Header/Desktop/ManageStudies-Link")
    assert locators.get("CRDC/AILocators/Global/Header/Desktop/ManagePrograms-Link")
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
    assert locators.get("CRDC/AILocators/Programs/List/Container")
    assert locators.get("CRDC/AILocators/Programs/List/AddProgram-Btn")
    assert locators.get("CRDC/AILocators/Programs/List/Filters/ProgramName-TxtBx")
    assert locators.get("CRDC/AILocators/Programs/List/Filters/StudyName-TxtBx")


@pytest.mark.unit
def test_missing_path_raises(locators: LocatorLoader) -> None:
    with pytest.raises(KeyError, match="Locator not found"):
        locators.get("CRDC/DoesNotExist/Missing-Btn")


@pytest.mark.unit
def test_katalon_placeholder_substitution(locators: LocatorLoader) -> None:
    xpath = locators.get("CRDC/ManageUsers/RoleDdn-Option", role="Admin")
    assert xpath == "//li[text()='Admin']"


@pytest.mark.unit
def test_brace_placeholder_substitution(locators: LocatorLoader) -> None:
    xpath = locators.get("CRDC/ManageUsers/RoleDdn-Option", role="Submitter")
    assert "Submitter" in xpath


@pytest.mark.unit
def test_attribute_access_normalizes_hyphens(locators: LocatorLoader) -> None:
    xpath = locators.CRDC.AILocators.Global.Header.Desktop.UserName_Btn
    assert "navbar-dropdown-name" in xpath
