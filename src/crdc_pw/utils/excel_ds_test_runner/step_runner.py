"""Execute Steps sheet actions for Data Submission metadata VR cases."""

from __future__ import annotations

import logging
from pathlib import Path

from crdc_pw.hub import Hub
from crdc_pw.pages.data_submissions import DataSubmissionDetailPage, DataSubmissionsListPage
from crdc_pw.utils.excel_ds_test_runner.loader import ExcelLoadError, load_steps

log = logging.getLogger("crdc_pw.utils.excel_ds_test_runner")

KNOWN_ACTIONS = (
    "open_data_submissions",
    "create_data_submission",
    "upload_metadata_folder",
    "click_validate",
    "verify_validation_results_for_tc",
)


def _norm_action(action: str) -> str:
    return action.strip().lower().replace(" ", "_").replace("-", "_")


def _split_pipe_params(params: str, *, count: int, action: str, path: Path, row: int) -> tuple[str, ...]:
    parts = [p.strip() for p in params.split("|")]
    if len(parts) != count:
        raise ExcelLoadError(
            f"{action} expects {count} pipe-separated Params values, got {len(parts)}",
            path=path,
            row=row,
        )
    return tuple(parts)


def run_testcase_excel(hub: Hub, excel_path: Path) -> None:
    """Run one TC*.xlsx test case (Settings role must match hub.role)."""
    path = Path(excel_path)
    input_root, steps = load_steps(path)
    log.info("Excel case %s (%d steps), input_root=%s", path.name, len(steps), input_root or "(none)")

    ds: DataSubmissionsListPage | None = None
    detail: DataSubmissionDetailPage | None = None

    for step in steps:
        action = _norm_action(step.action)
        log.info("Step row %s: %s", step.excel_row, action)

        if action == "open_data_submissions":
            ds = DataSubmissionsListPage(hub.page, hub.locators)
            ds.open()
        elif action == "create_data_submission":
            sub_type, data_type, model, study = _split_pipe_params(
                step.params, count=4, action=action, path=path, row=step.excel_row
            )
            if ds is None:
                ds = DataSubmissionsListPage(hub.page, hub.locators)
            ds.create_data_submission(sub_type, data_type, model, study)
            detail = DataSubmissionDetailPage(hub.page, hub.locators)
        elif action == "upload_metadata_folder":
            folder = step.params
            if not folder:
                raise ExcelLoadError("upload_metadata_folder needs folder name in Params", path=path, row=step.excel_row)
            if detail is None:
                detail = DataSubmissionDetailPage(hub.page, hub.locators)
            detail.upload_folder(folder)
        elif action == "click_validate":
            if detail is None:
                detail = DataSubmissionDetailPage(hub.page, hub.locators)
            detail.click_validate()
        elif action == "verify_validation_results_for_tc":
            tc_name = step.params
            model = step.model
            if not tc_name or not model:
                raise ExcelLoadError(
                    "verify_validation_results_for_tc needs tc name in Params and model in Model",
                    path=path,
                    row=step.excel_row,
                )
            if detail is None:
                detail = DataSubmissionDetailPage(hub.page, hub.locators)
            detail.verify_validation_results_vs_expected_for_tc(tc_name, model=model)
        else:
            raise ExcelLoadError(
                f"Unknown step action {step.action!r}. Use one of: {', '.join(KNOWN_ACTIONS)}",
                path=path,
                row=step.excel_row,
            )
