"""No-browser guards for CRDCDH-332 TC01 (Submission Request AllFields).

The form page joins a folder prefix with a field name (for example Section-A/ plus
AddContact-Btn), so test_locator_contract cannot see those paths. This file lists them
and checks the Excel rows and columns the fill and Review verify methods read.
"""

from __future__ import annotations

import pytest

from crdc_pw.locators.loader import LocatorLoader
from crdc_pw.pages.submission_request_form import (
    _REVIEW_DATA_TYPES,
    _cell_text,
    _digits,
    _squash,
)
from crdc_pw.utils.submission_request_excel import find_cell_containing, get_sheet_row

pytestmark = pytest.mark.unit

_A = "CRDC/SubmissionRequest/Section-A/"
_B = "CRDC/SubmissionRequest/Section-B/"
_R = "CRDC/SubmissionRequest/ReviewSubmit/"
_D = "CRDC/SubmissionRequest/Section-D/"

_FILL_KEYS = [
    _A + name
    for name in (
        "AddContact-Btn",
        "AC_FirstName-Txtbx",
        "AC_LastName-Txtbx",
        "AC_Position-Txtbx",
        "AC_Email-Txtbx",
        "AC_Institution-Dd",
        "AC_Phone-Txtbx",
    )
] + [
    _B + name
    for name in (
        "AddExistingPublication-Btn",
        "PublicationTitle-TxtBx",
        "PubMedID-Txtbx",
        "DOI-Txtbx",
        "AddPlannedPublication-Btn",
        "PlannedPublicationTitle-Txtbx",
        "ExpectedPubDate-Clndr",
        "AddRepository-Btn",
        "RepositoryName-Txtbx",
        "StudyID-Txtbx",
        "DataTypesSubmitd-Dd",
        "OtherDataTypes-Txtbx",
    )
]

_REVIEW_KEYS = [
    _R + name
    for name in (
        "PI_Name-Txt",
        "PI_Position-Txt",
        "PI_Email-Txt",
        "PI_InstitName-Txt",
        "PI_InstitAddress-Txt",
        "PC_Name-Txt",
        "PC_Position-Txt",
        "PC_Email-Txt",
        "PC_InstitName-Txt",
        "PC_Phone-Txt",
        "AC_Name-Txt",
        "AC_Position-Txt",
        "AC_Email-Txt",
        "AC_InstitName-Txt",
        "AC_Phone-Txt",
        "ProgramTitle-Txt",
        "ProgAbbre-Txt",
        "ProgDescrptn-Txt",
        "StudyTitle-Txt",
        "StudyAbbre-Txt",
        "StudyDscrptin-Txt",
        "FndngAgncy-Txt",
        "GrantCntractNum-Txt",
        "NCIProgOficer-Txt",
        "PublictnTitle-Txt",
        "PubMedID-Txt",
        "DOI-Txt",
        "PlnedPublTitle-Txt",
        "ExpctdPubDate-Txt",
        "RepoName-Txt",
        "StudyID-Txt",
        "RepositoryOtherDataTypes-Txt",
        "AccessTypes-Txt",
        "CancerTypes-Txt",
        "PreCancerTypes-Txt",
        "SpeciesOfSubject-Txt",
        "NumOfSubjInclud-Txt",
        "CellLines-Txt",
        "DataDeIdentified-Txt",
        "TragetSubmDelivryDate-Txt",
        "ExpctdPubliDateSec-D-RevPage-Txt",
        "FileType-RowOne-Txt",
        "FileExtension-Txt",
        "NumOfFiles-RowOne-Txt",
        "EstimDtaSiz-RowOne-Txt",
        "AdditionalComnt-Txt",
    )
]


def test_tc01_fill_locators_exist(locators: LocatorLoader) -> None:
    missing = [path for path in _FILL_KEYS if not locators.has(path)]
    assert missing == [], f"fill locators not in YAML: {missing}"


def test_tc01_review_locators_exist(locators: LocatorLoader) -> None:
    missing = [path for path in _REVIEW_KEYS if not locators.has(path)]
    assert missing == [], f"Review locators not in YAML: {missing}"


def test_review_data_type_locators_exist(locators: LocatorLoader) -> None:
    missing = [
        _R + key for key, _column in _REVIEW_DATA_TYPES.values() if not locators.has(_R + key)
    ]
    assert missing == [], f"data type Review locators not in YAML: {missing}"


def test_tc01_excel_rows_have_every_column_the_flow_reads() -> None:
    """Rows and columns TC01 passes to the fill and verify methods all have a value."""
    needs = {
        ("section-a", 2): [
            "pi-first-name", "pi-last-name", "position", "pi-email", "pi-institution",
            "pi-instit-address", "pc-first-name", "pc-last-name", "pc-position", "pc-email",
            "pc-institution", "pc-phone", "ac-first-name", "ac-last-name", "ac-position",
            "ac-email", "ac-institution", "ac-phone",
        ],
        ("section-b", 6): ["program-title", "prog-abbreviation", "prog-description"],
        ("section-b", 1): [
            "study-title", "study-abbreviation", "study-description", "funding-agency",
            "grant-number", "nci-prog-officer", "publication-title", "pubmed-id", "doi",
            "pland-publictn-title", "repository-name", "study-id", "other-data-types",
        ],
        ("section-c", 1): [
            "access-types", "pre-cancer-type", "num-of-subjects-included", "cell-lines",
            "data-de-identified",
        ],
        ("section-d", 1): ["addit-comnt", "othr-clinicl"],
        ("section-d", 2): ["genomics", "proteomics"],
        ("section-d", 5): ["file-type"],
        ("section-d", 6): ["file-extension"],
    }
    empty: list[str] = []
    for (sheet, row_num), columns in needs.items():
        row = get_sheet_row(sheet, row_num)
        for column in columns:
            if column not in row or not str(row[column] if row[column] is not None else "").strip():
                empty.append(f"{sheet} row {row_num}: {column}")
    assert empty == [], f"SubmissionRequest.xlsx cells TC01 reads are empty: {empty}"


def test_find_cell_containing_maps_dropdown_words_to_list_values() -> None:
    assert (
        find_cell_containing("section-c", "cancer-type", "Cholangiocarcinoma")
        == "Bile Duct, Cholangiocarcinoma"
    )
    assert find_cell_containing("section-c", "pre-cancer-type", "lung") == "Lung Cancer"
    assert find_cell_containing("section-c", "species-of-subject", "Homo") == "Homo sapiens"


def test_find_cell_containing_rejects_unknown_word_and_column() -> None:
    with pytest.raises(LookupError):
        find_cell_containing("section-c", "cancer-type", "no-such-cancer")
    with pytest.raises(KeyError):
        find_cell_containing("section-c", "no-such-column", "x")


def test_cell_text_and_squash_helpers() -> None:
    assert _cell_text(34543543345) == "34543543345"
    assert _cell_text(1.0) == "1"
    assert _cell_text(None) == ""
    assert _cell_text(" abc ") == "abc"
    assert _squash("a  b\n c ") == "a b c"


def test_digits_makes_excel_and_review_phone_formats_equal() -> None:
    """Excel has 404-588-3432; the Review page shows (404)588-3432."""
    assert _digits("404-588-3432") == _digits("(404)588-3432") == "4045883432"
    assert _digits("676-654-3232") == _digits("(676)654-3232")
    assert _digits("404-588-3432") != _digits("(404)588-3433")
    assert _digits(None) == ""  # type: ignore[arg-type]
