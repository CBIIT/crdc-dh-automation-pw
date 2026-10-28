# CRDC object repository — conversion report

- Source: 745 Katalon locators in 7 folders
- Removed as duplicates: 24
- Kept: 721 locators in 91 YAML files

## Removed duplicates
If a script still uses a removed path, use the `Use instead` path.

| Removed | Use instead | Reason |
|---|---|---|
| `CRDC/DataSubmissions/AdminSubmit-Btn` | `CRDC/AILocators/DataSubmissions/Detail/Actions/AdminSubmit-Btn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Cancel-Btn` | `CRDC/AILocators/DataSubmissions/Detail/Actions/Cancel-Btn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Complete-Btn` | `CRDC/AILocators/DataSubmissions/Detail/Actions/Complete-Btn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Create/Create-Btn` | `CRDC/AILocators/DataSubmissions/CreateDialog/Create-Btn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Create/CreateADataSubmission-Btn` | `CRDC/AILocators/DataSubmissions/List/Table/CreateDataSubmission-Btn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Create/SubmissionName-Field` | `CRDC/AILocators/DataSubmissions/CreateDialog/SubmissionName-TxtBx` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/DataSubmissionName-Link` | `CRDC/AILocators/DataSubmissions/Detail/Tabs/UploadActivities-Tab` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Reject-Btn` | `CRDC/AILocators/DataSubmissions/Detail/Actions/Reject-Btn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Submit-Btn` | `CRDC/AILocators/DataSubmissions/Detail/Actions/Submit-Btn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/SubmitYes-Btn` | `CRDC/AILocators/DataSubmissions/Detail/Actions/CompleteConfirmationYes-Btn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Validation/DSDashboard-Status-Lbl` | `CRDC/AILocators/DataSubmissions/Detail/Summary/Status-Lbl` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Validation/ValidationTarget-AllUploadedData-RadioBtn` | `CRDC/AILocators/DataSubmissions/Detail/ValidationControls/ValidationTarget-AllUploadedData-RadioBtn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Validation/ValidationTarget-NewUploadedData-RadioBtn` | `CRDC/AILocators/DataSubmissions/Detail/ValidationControls/ValidationTarget-NewUploadedData-RadioBtn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Validation/ValidationType-Both-RadioBtn` | `CRDC/AILocators/DataSubmissions/Detail/ValidationControls/ValidationType-Both-RadioBtn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Validation/ValidationType-Metadata-RadioBtn` | `CRDC/AILocators/DataSubmissions/Detail/ValidationControls/ValidationType-Metadata-RadioBtn` | same XPath exists in AILocators |
| `CRDC/DataSubmissions/Withdraw-Btn` | `CRDC/AILocators/DataSubmissions/Detail/Actions/Withdraw-Btn` | same XPath exists in AILocators |
| `CRDC/ManageUsers/Next-Btn` | `CRDC/AILocators/GenericTable/Pagination/NextPage-Btn` | same XPath exists in AILocators |
| `CRDC/SubmissionRequest/Progress-Bar/Full-History-Btn` | `CRDC/AILocators/SubmissionRequests/StatusBar/FullHistory-Btn` | same XPath exists in AILocators |
| `CRDC/SubmissionRequest/Progress-Bar/LastUpdated-Date` | `CRDC/AILocators/SubmissionRequests/StatusBar/LastUpdated-Lbl` | same XPath exists in AILocators |
| `CRDC/SubmissionRequest/Progress-Bar/StatusBar-Stutus` | `CRDC/AILocators/SubmissionRequests/StatusBar/Status-Lbl` | same XPath exists in AILocators |
| `CRDC/SubmissionRequest/ReadAndAcceptPopUp-Btn` | `CRDC/AILocators/SubmissionRequests/Form/Review/CancelSubmissionRequestConfirm-Btn` | same XPath exists in AILocators |
| `CRDC/SubmissionRequest/Status-Bar/Full-History-Btn` | `CRDC/AILocators/SubmissionRequests/StatusBar/FullHistory-Btn` | same XPath exists in AILocators |
| `CRDC/SubmissionRequest/Status-Bar/LastUpdated-Date` | `CRDC/AILocators/SubmissionRequests/StatusBar/LastUpdated-Lbl` | same XPath exists in AILocators |
| `CRDC/SubmissionRequest/Status-Bar/StatusBar-Stutus` | `CRDC/AILocators/SubmissionRequests/StatusBar/Status-Lbl` | same XPath exists in AILocators |

## Same XPath under different names (kept)
Not removed because tests may use each name. Review if you want to merge them.

| Locators | XPath |
|---|---|
| `CRDC/AILocators/DataExplorer/List/Filters/DbGaPID-TxtBx`<br>`CRDC/AILocators/DataSubmissions/List/Filters/DbGaPID-TxtBx`<br>`CRDC/AILocators/Studies/Detail/DbGaPID-TxtBx`<br>`CRDC/AILocators/Studies/List/Filters/DbGaPID-TxtBx` | `//*[@data-testid='dbGaPID-input']` |
| `CRDC/AILocators/DataExplorer/List/Filters/ResetFilters-Btn`<br>`CRDC/AILocators/DataSubmissions/List/Filters/ResetFilters-Btn`<br>`CRDC/AILocators/SubmissionRequests/List/Filters/ResetFilters-Btn` | `//*[@data-testid='reset-filters-button']` |
| `CRDC/AILocators/DataExplorer/StudyView/ColumnVisibility-Btn`<br>`CRDC/AILocators/DataSubmissions/List/Filters/ColumnVisibility-Btn` | `//*[@data-testid='column-visibility-button']` |
| `CRDC/AILocators/DataExplorer/StudyView/Container`<br>`CRDC/AILocators/Studies/Detail/Container` | `//*[@data-testid='study-view-container']` |
| `CRDC/AILocators/DataSubmissions/Detail/Actions/Cancel-Btn`<br>`CRDC/AILocators/Organizations/Detail/Cancel-Btn`<br>`CRDC/AILocators/SubmissionRequests/SubmitFormDialog/Cancel-Btn`<br>`CRDC/AILocators/SubmissionRequests/UnsavedChangesDialog/Cancel-Btn`<br>`CRDC/AILocators/Users/Profile/Cancel-Btn` | `//button[.='Cancel']` |
| `CRDC/AILocators/DataSubmissions/Detail/Actions/CompleteConfirmationYes-Btn`<br>`CRDC/AILocators/DataSubmissions/Detail/Actions/ReleaseConfirmationYes-Btn` | `//button[.='Yes']` |
| `CRDC/AILocators/DataSubmissions/Detail/Actions/ConfirmToReject-Btn`<br>`CRDC/AILocators/SubmissionRequests/RejectDialog/ConfirmReject-Btn` | `//button[.='Confirm to Reject']` |
| `CRDC/AILocators/DataSubmissions/Detail/CrossValidation/Table-Row`<br>`CRDC/AILocators/DataSubmissions/List/Table/TableRow`<br>`CRDC/AILocators/GenericTable/TableRow` | `//*[@data-testid='generic-table-row']` |
| `CRDC/AILocators/DataSubmissions/List/Filters/Status-Ddn`<br>`CRDC/AILocators/Institutions/Detail/Status-Ddn` | `//*[@data-testid='status-select']` |
| `CRDC/AILocators/DataSubmissions/List/Table/Table`<br>`CRDC/AILocators/GenericTable/Table` | `//*[@data-testid='generic-table']` |
| `CRDC/AILocators/DataSubmissions/List/Table/TableBody`<br>`CRDC/AILocators/GenericTable/TableBody` | `//*[@data-testid='generic-table-body']` |
| `CRDC/AILocators/Institutions/Detail/Cancel-Btn`<br>`CRDC/AILocators/Studies/Detail/Cancel-Btn` | `//*[@data-testid='cancel-button']` |
| `CRDC/AILocators/Institutions/Detail/Save-Btn`<br>`CRDC/AILocators/Studies/Detail/Save-Btn` | `//*[@data-testid='save-button']` |
| `CRDC/AILocators/Login/LoginPageContent`<br>`CRDC/AILocators/Login/RulesOfUseContent` | `//main[@id='main-content']` |
| `CRDC/AILocators/Organizations/Detail/Save-Btn`<br>`CRDC/AILocators/SubmissionRequests/UnsavedChangesDialog/Save-Btn`<br>`CRDC/AILocators/Users/Profile/Save-Btn` | `//button[.='Save']` |
| `CRDC/AILocators/Organizations/List/AddProgram-Btn`<br>`CRDC/AILocators/Programs/List/AddProgram-Btn` | `//a[.='Add Program']` |
| `CRDC/AILocators/Organizations/List/ProgramFilter-TxtBx`<br>`CRDC/AILocators/Programs/List/Filters/ProgramName-TxtBx` | `//*[@id='organization-filter']` |
| `CRDC/AILocators/Organizations/List/StatusFilter-Ddn`<br>`CRDC/AILocators/Users/List/StatusFilter-Ddn` | `//*[@id='status-filter']` |
| `CRDC/AILocators/Organizations/List/StudyFilter-TxtBx`<br>`CRDC/AILocators/Programs/List/Filters/StudyName-TxtBx` | `//*[@id='study-filter']` |
| `CRDC/DataSubmissions/DataSubmListTable-Row`<br>`CRDC/DataSubmissions/Validation/Table-Row`<br>`CRDC/SubmissionRequest/SubmReqListTable-Row` | `//tbody/tr` |
| `CRDC/DataSubmissions/Uploading-Txt`<br>`CRDC/DataSubmissions/Validation/Uploading-Text` | `//*[.='Uploading']` |
| `CRDC/DataSubmissions/Validation/Download-Btn-ValidationResults`<br>`CRDC/DataSubmissions/Validation/export-validation-button` | `//button[@data-testid='export-validation-button']` |
| `CRDC/DataSubmissions/Validation/NodeType-Ddn`<br>`CRDC/DataSubmissions/Validation/ValidationResults_NodeType-Ddn` | `//div[@id='mui-component-select-nodeType']` |
| `CRDC/SubmissionRequest/PopUpConfirmToSubmit-Btn`<br>`CRDC/SubmissionRequest/Start_a_SubmissionRequest-Btn` | `//*[contains(@id, ':r') and @type='button']` |
| `CRDC/SubmissionRequest/Section-A/SameAsPrincipaInvestigtr-ChkBx`<br>`CRDC/SubmissionRequest/Section-A/SameAsPrincipal-ChkBx` | `//*[@class='PrivateSwitchBase-input css-1m9pwf3' and @type='checkbox']` |
| `CRDC/SubmissionRequest/Section-B/Program-Dd`<br>`CRDC/SubmissionRequest/Section-B/Program-Field` | `//*[@id="section-b-program"]` |
| `CRDC/SubmissionRequest/Section-B/RemovePlannedPublication-Btn`<br>`CRDC/SubmissionRequest/Section-B/RemovePublication-Btn` | `//*[@id="section-b-publication-0-remove-publication-button"]` |
| `CRDC/SubmissionRequest/Section-B/RepositoryStudyID-Txtbx`<br>`CRDC/SubmissionRequest/Section-B/StudyID-Txtbx` | `//*[@id="section-b-repository-0-study-id"]` |
| `CRDC/SubmissionRequest/Section-C/OtherCancerTypes-Chkbx`<br>`CRDC/SubmissionRequest/Section-C/OtherSpecieInvolved-Chkbx` | `//*[@id="section-c-other-cancer-types-enabled-label-checkbox"]` |
| `CRDC/SubmissionRequest/Section-D/TragetSubmDelivryDate-Clnder`<br>`CRDC/SubmissionRequest/Section-D/TragetSubmissionDelivryDate-Clnder` | `//*[@id="section-d-targeted-data-submission-delivery-date"]//following::button[1]` |
