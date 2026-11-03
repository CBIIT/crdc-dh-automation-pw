"""Katalon utilities.SubmissionRequest workflow facade (inquire/approve/reopen, fill orchestration).

Section A–D Excel filling currently lives here; planned home is SubmissionRequestFormPage.
See docs/sr-form-section-fill-refactor.md.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from playwright.sync_api import Page

from crdc_pw.locators.loader import LocatorLoader
from crdc_pw.pages.submission_request_form import SubmissionRequestFormPage
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage
from crdc_pw.utils.submission_request_excel import get_sheet_row

log = logging.getLogger("crdc_pw.submission_request")

# Section A (AILocators)
_A_PI_FN = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-FirstName-TxtBx"
_A_PI_LN = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-LastName-TxtBx"
_A_PI_POS = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-Position-TxtBx"
_A_PI_EMAIL = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-Email-TxtBx"
_A_PI_INST = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-Institution-Ddn"
_A_PI_ADDR = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PI-Address-TxtBx"
_A_PC_FN = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-FirstName-TxtBx"
_A_PC_LN = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-LastName-TxtBx"
_A_PC_POS = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-Position-TxtBx"
_A_PC_EMAIL = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-Email-TxtBx"
_A_PC_INST = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-Institution-Ddn"
_A_PC_PHONE = "CRDC/AILocators/SubmissionRequests/Form/SectionA/PrimaryContact-Phone-TxtBx"

# Section B
_B_PROGRAM = "CRDC/AILocators/SubmissionRequests/Form/SectionB/Program-Ddn"
_B_PROG_TITLE = "CRDC/AILocators/SubmissionRequests/Form/SectionB/ProgramTitle-TxtBx"
_B_PROG_ABBR = "CRDC/AILocators/SubmissionRequests/Form/SectionB/ProgramAbbreviation-TxtBx"
_B_PROG_DESC = "CRDC/AILocators/SubmissionRequests/Form/SectionB/ProgramDescription-TxtBx"
_B_STUDY_TITLE = "CRDC/AILocators/SubmissionRequests/Form/SectionB/StudyTitle-TxtBx"
_B_STUDY_ABBR = "CRDC/AILocators/SubmissionRequests/Form/SectionB/StudyAbbreviation-TxtBx"
_B_STUDY_DESC = "CRDC/AILocators/SubmissionRequests/Form/SectionB/StudyDescription-TxtBx"
_B_FUND_AGENCY = "CRDC/SubmissionRequest/Section-B/FundingAgency-Dd"
_B_GRANT = "CRDC/SubmissionRequest/Section-B/GrantContractNumber-Txtbx"
_B_NCI_OFF = "CRDC/SubmissionRequest/Section-B/NCIProgramOfficer-Txtbx"

# Section C (legacy paths — stable ids)
_C_OPEN = "CRDC/SubmissionRequest/Section-C/OpenAccess-ChkBx"
_C_CONTROLLED = "CRDC/SubmissionRequest/Section-C/ControlledAccess-Chkbx"
_C_DBGAP = "CRDC/SubmissionRequest/Section-C/dbGapRegistered-TogleBtn"
_C_DBGAP_PHS = "CRDC/SubmissionRequest/Section-C/dbGapPHSNumber-Txtbx"
_C_CANCER = "CRDC/SubmissionRequest/Section-C/CancerTypes-Dd"
_C_PRE_CANCER = "CRDC/SubmissionRequest/Section-C/PreCancerTypes-Txtbx"
_C_SPECIES = "CRDC/SubmissionRequest/Section-C/SpeciesOfSubjects-Dd"
_C_NUM_SUBJ = "CRDC/SubmissionRequest/Section-C/NumOfSubjectsIncludInSub-Txtbx"

# Section D
_D_TARGET_DATE = "CRDC/SubmissionRequest/Section-D/TragetSubmDelivryDate-TxtBx"
_D_PUB_DATE = "CRDC/SubmissionRequest/Section-D/ExpctdPublicationDate-TxtBx"
_D_FILE_TYPE = "CRDC/SubmissionRequest/Section-D/FileType-RowOne-Dd"
_D_FILE_EXT = "CRDC/SubmissionRequest/Section-D/FileExtension-RowOne-Dd"
_D_NUM_FILES = "CRDC/SubmissionRequest/Section-D/NumOfFiles-RowOne-Txtbx"
_D_DATA_SIZE = "CRDC/SubmissionRequest/Section-D/EstimDtaSiz-RowOne-Txtbx"
_D_DEID_YES = "CRDC/SubmissionRequest/Section-D/ConfirmDataIdentified_yes-RdoBtn"
_D_COMMENT = "CRDC/SubmissionRequest/Section-D/AdditionalComnt-TxtBx"
_DD_VALUE = "CRDC/SubmissionRequest/CrdcDdValue"
_TOGGLE = "CRDC/SubmissionRequest/Toggle-Btn"


def _stamp() -> str:
    """Unique suffix for study/program names (Katalon M-d-yyyy-HH-mm plus seconds)."""
    now = datetime.now()
    return (
        f"{now.month}-{now.day}-{now.year}-"
        f"{now.hour:02d}-{now.minute:02d}-{now.second:02d}"
    )


def _s(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


class SubmissionRequest:
    """Port of utilities.SubmissionRequest static state + @Keyword methods."""

    last_entered_study_title: str | None = None
    last_entered_study_abbreviation: str | None = None
    last_entered_program_name: str | None = None

    def __init__(self, page: Page, locators: LocatorLoader) -> None:
        self.page = page
        self.locators = locators
        self.form = SubmissionRequestFormPage(page, locators)
        self.list = SubmissionRequestsListPage(page, locators)

    def _loc(self, path: str, **kw: str):
        return self.form._loc(path, **kw)

    def _fill_if_empty(self, path: str, value: str) -> None:
        field = self._loc(path).first
        field.wait_for(state="visible", timeout=20_000)
        existing = field.input_value()
        if existing and existing.strip():
            log.info("Skipping %s (already has value)", path)
            return
        field.fill(_s(value))

    def _fill(self, path: str, value: str) -> None:
        field = self._loc(path).first
        field.wait_for(state="visible", timeout=20_000)
        field.click()
        field.fill(_s(value))

    def _click_dd_option(self, dd_path: str, option_text: str) -> None:
        self._loc(dd_path).first.click()
        self.page.wait_for_timeout(500)
        xpath = self.locators.get(
            _DD_VALUE, **{"GlobalVariable.CrdcUiElement": option_text}
        )
        opt = self.page.locator(xpath).first
        opt.scroll_into_view_if_needed()
        opt.click()

    def enter_principal_investigator_info(self, data_row_num: int) -> None:
        row = get_sheet_row("section-a", data_row_num)
        mapping = [
            (_A_PI_FN, "pi-first-name"),
            (_A_PI_LN, "pi-last-name"),
            (_A_PI_POS, "position"),
            (_A_PI_EMAIL, "pi-email"),
            (_A_PI_INST, "pi-institution"),
            (_A_PI_ADDR, "pi-instit-address"),
        ]
        for path, key in mapping:
            field = self._loc(path).first
            field.wait_for(state="visible", timeout=20_000)
            new_val = _s(row.get(key))
            if key == "pi-email":
                field.click()
                field.fill(new_val)
                log.info("PI email set from test data")
            else:
                self._fill_if_empty(path, new_val)

    def enter_primary_contact_info(self, data_row_num: int) -> None:
        row = get_sheet_row("section-a", data_row_num)
        for path, key in [
            (_A_PC_FN, "pc-first-name"),
            (_A_PC_LN, "pc-last-name"),
            (_A_PC_POS, "pc-position"),
            (_A_PC_EMAIL, "pc-email"),
            (_A_PC_INST, "pc-institution"),
            (_A_PC_PHONE, "pc-phone"),
        ]:
            self._fill(path, _s(row.get(key)))

    def enter_program_info(self, dd_value: str, data_row_num: int) -> None:
        row = get_sheet_row("section-b", data_row_num)
        ts = _stamp()
        self._click_dd_option(_B_PROGRAM, dd_value)
        if "Other" in dd_value:
            base_title = _s(row.get("program-title"))
            SubmissionRequest.last_entered_program_name = base_title + ts
            self._fill(_B_PROG_TITLE, SubmissionRequest.last_entered_program_name)
            self._fill(
                _B_PROG_ABBR, _s(row.get("prog-abbreviation")) + ts
            )
            self._fill(_B_PROG_DESC, _s(row.get("prog-description")))
        elif any(x in dd_value for x in ("CCDI", "CPTAC", "DCCPS", "HTAN")):
            SubmissionRequest.last_entered_program_name = None
        else:
            raise ValueError(f"Unsupported program dropdown value: {dd_value!r}")

    def enter_study_info(self, data_row_num: int) -> None:
        row = get_sheet_row("section-b", data_row_num)
        ts = _stamp()
        title = _s(row.get("study-title")) + ts
        abbrev = _s(row.get("study-abbreviation")) + ts
        SubmissionRequest.last_entered_study_title = title
        SubmissionRequest.last_entered_study_abbreviation = abbrev
        self._fill(_B_STUDY_TITLE, title)
        self._fill(_B_STUDY_ABBR, abbrev)
        self._fill(_B_STUDY_DESC, _s(row.get("study-description")))

    def enter_funding_agency_info(self, data_row_num: int) -> None:
        row = get_sheet_row("section-b", data_row_num)
        self._fill(_B_FUND_AGENCY, _s(row.get("funding-agency")))
        self._fill(_B_GRANT, _s(row.get("grant-number")))
        self._fill(_B_NCI_OFF, _s(row.get("nci-prog-officer")))

    def enter_data_access_type_and_dbgap_reg_info(
        self, access_type: str, db_gap_registered: str
    ) -> None:
        access = access_type.strip().lower()
        if access == "open":
            self._loc(_C_OPEN).first.click()
        elif access == "controlled":
            self._loc(_C_CONTROLLED).first.click()
        elif access == "both":
            self._loc(_C_OPEN).first.click()
            self._loc(_C_CONTROLLED).first.click()
        else:
            raise ValueError(f"Invalid access type: {access_type!r}")
        if db_gap_registered.strip().lower() == "yes":
            self._loc(_C_DBGAP).first.click()
            self._fill(_C_DBGAP_PHS, "phs005555")

    def enter_cancer_type_and_subjects_info(
        self, cancer_type: str, species_of_subjects: str, data_row_num: int
    ) -> None:
        row = get_sheet_row("section-c", data_row_num)
        self._click_dd_option(_C_CANCER, cancer_type)
        self.page.keyboard.press("Tab")
        self._fill(_C_PRE_CANCER, _s(row.get("pre-cancer-type")))
        self._click_dd_option(_C_SPECIES, species_of_subjects)
        self.page.keyboard.press("Tab")
        self._fill(_C_NUM_SUBJ, _s(row.get("num-of-subjects-included")))

    def enter_target_delivery_and_expected_publication_date(self) -> None:
        from crdc_pw.pages.submission_request_form import SR_QUESTIONNAIRE_FUTURE_DATE

        self._fill(_D_TARGET_DATE, SR_QUESTIONNAIRE_FUTURE_DATE)
        self._fill(_D_PUB_DATE, SR_QUESTIONNAIRE_FUTURE_DATE)

    def select_data_types(self, *labels: str) -> None:
        self.page.wait_for_timeout(1000)
        for raw in labels:
            label = raw.lower()
            if "other" in label and label != "other-clinical":
                row = get_sheet_row("section-d", 1)
                self._fill(
                    "CRDC/SubmissionRequest/Section-D/OthrDtaTyp-Txtbx",
                    _s(row.get("other")),
                )
            elif label == "other-clinical":
                row = get_sheet_row("section-d", 1)
                self._fill(
                    "CRDC/SubmissionRequest/Section-D/OthrClinclDtaTyp-Txtbx",
                    _s(row.get("othr-clinicl")),
                )
            elif "imaging" in label:
                xpath = self.locators.get(
                    _TOGGLE, **{"GlobalVariable.CrdcUiElement": label}
                )
                self.page.locator(xpath).first.click()
                self._loc(_D_DEID_YES).first.click()
            else:
                toggle = self.page.locator(
                    f"//*[contains(@id,{_xpath_literal(label)}) and @type='checkbox']"
                ).first
                toggle.click()

    def select_file_types(
        self,
        file_type_row: int,
        file_extension_row: int,
        num_of_files_row: int,
        estimated_data_size_row: int,
    ) -> None:
        ft_row = get_sheet_row("section-d", file_type_row)
        fe_row = get_sheet_row("section-d", file_extension_row)
        nf_row = get_sheet_row("section-d", num_of_files_row)
        sz_row = get_sheet_row("section-d", estimated_data_size_row)
        file_type = _s(ft_row.get("file-type"))
        file_ext = _s(fe_row.get("file-extension"))
        self._loc(_D_FILE_TYPE).first.scroll_into_view_if_needed()
        self._click_dd_option(_D_FILE_TYPE, file_type)
        self._click_dd_option(_D_FILE_EXT, file_ext)
        self._fill(_D_NUM_FILES, _s(nf_row.get("num-of-file")))
        self._fill(_D_DATA_SIZE, _s(sz_row.get("estimtd-data-size")))
        self._loc(_D_DEID_YES).first.click()
        comment_row = get_sheet_row("section-d", 1)
        self._fill(_D_COMMENT, _s(comment_row.get("addit-comnt")))

    def fill_submission_request_all_sections(
        self,
        section_a_row: int,
        program_dd: str,
        program_data_row: int,
        study_data_row: int,
        funding_data_row: int,
        data_access_type: str,
        db_gap_registered: str,
        cancer_type: str,
        species_of_subjects: str,
        section_c_data_row: int,
        first_data_type: str,
        second_data_type: str,
        file_type_row: int,
        file_extension_row: int,
        num_of_files_row: int,
        estimated_data_size_row: int,
    ) -> None:
        self.enter_principal_investigator_info(section_a_row)
        self.enter_primary_contact_info(section_a_row)
        self.form.click_save()
        self.form.click_next()
        self.form.assert_status("IN PROGRESS")

        self.enter_program_info(program_dd, program_data_row)
        self.enter_study_info(study_data_row)
        self.enter_funding_agency_info(funding_data_row)
        self.form.click_save()
        self.form.click_next()

        self.enter_data_access_type_and_dbgap_reg_info(
            data_access_type, db_gap_registered
        )
        self.enter_cancer_type_and_subjects_info(
            cancer_type, species_of_subjects, section_c_data_row
        )
        self.form.click_save()
        self.form.click_next()

        self.enter_target_delivery_and_expected_publication_date()
        self.select_data_types(first_data_type, second_data_type)
        self.select_file_types(
            file_type_row,
            file_extension_row,
            num_of_files_row,
            estimated_data_size_row,
        )
        self.form.click_save()
        self.form.click_next()

    def click_submit_button(self) -> None:
        self.form.click_submit_button()

    def open_submission_request_form_for_study(
        self, study_name: str, list_status: str | None = None
    ) -> None:
        self.list.open_submission_request_form_for_study(study_name, list_status)

    def inquire_submission_request(
        self, study_name: str, inquire_comment: str | None = None
    ) -> None:
        self._open_submission_request_review(study_name)
        self.form.inquire_with_comment(
            inquire_comment or "Automated test inquire - CRDC submission request."
        )

    def approve_submission_request(
        self, study_name: str, approval_comment: str | None = None
    ) -> None:
        self._open_submission_request_review(study_name)
        self.form.approve_with_comment(
            approval_comment or "Automated test approval - CRDC submission request."
        )

    def reopen_approved_submission_request(self, study_name: str) -> None:
        self.list.reopen_approved_submission_request(study_name)

    def _open_submission_request_review(self, study_name: str) -> None:
        token = (study_name or "").strip()
        if len(token) < 3:
            raise ValueError("study_name must be at least 3 characters")
        self.list.open()
        self.list.apply_submission_requests_list_filters({"study": token})
        self.page.wait_for_timeout(2000)
        self.list.click_review_for_study_row(token)
        self.form.click_review_progress_bar()


def _xpath_literal(text: str) -> str:
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    parts = text.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"
