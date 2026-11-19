"""No-browser checks for the upload CLI runner (CRDCDH-1405 TC101). The CLI itself is not run.

Flow (this file):
  1. build_config for data file and metadata, and its validation
  2. write_config_file holds the token with owner-only permissions
  3. mask_token
  4. cli_output_problems: good run, failure lines, missing lines, validation progress
  5. run_uploader raises when the CLI folder is missing
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
import yaml

from crdc_pw.utils.cli_uploader import (
    TYPE_DATA_FILE,
    TYPE_METADATA,
    CliResult,
    build_config,
    cli_dir,
    cli_output_problems,
    mask_token,
    run_uploader,
    write_config_file,
)

pytestmark = pytest.mark.unit

_GOOD_OUTPUT = """\
2 out of 3 file(s) have been validated.
3 out of 3 file(s) have been validated.
File uploading completed!
Files processed: 3
Files copied: 3
Files failed: 0
"""


def test_build_config_data_file(tmp_path: Path) -> None:
    config = build_config(
        api_url="https://hub/api/graphql",
        token="tok",
        submission_id="sub-1",
        upload_type=TYPE_DATA_FILE,
        data_dir=tmp_path,
        manifest=tmp_path / "manifest.tsv",
    )
    assert config == {
        "Config": {
            "api-url": "https://hub/api/graphql",
            "token": "tok",
            "submission": "sub-1",
            "type": "data file",
            "data": str(tmp_path.resolve()),
            "manifest": str((tmp_path / "manifest.tsv").resolve()),
            "retries": 3,
            "overwrite": False,
            "dryrun": False,
        }
    }


def test_build_config_metadata_has_no_manifest(tmp_path: Path) -> None:
    config = build_config(
        api_url="u", token="t", submission_id="s", upload_type=TYPE_METADATA, data_dir=tmp_path
    )
    assert "manifest" not in config["Config"]


def test_build_config_rejects_bad_input(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        build_config(api_url="u", token="t", submission_id="s", upload_type="zip", data_dir=tmp_path)
    with pytest.raises(ValueError):
        build_config(api_url="u", token="t", submission_id="s", upload_type=TYPE_DATA_FILE, data_dir=tmp_path)


def test_write_config_file_round_trips_and_is_private(tmp_path: Path) -> None:
    config = build_config(
        api_url="u", token='to"k: en', submission_id="s", upload_type=TYPE_METADATA, data_dir=tmp_path
    )
    path = write_config_file(config, tmp_path)
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == config
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_mask_token() -> None:
    assert mask_token("token=abc and abc", "abc") == "token=*** and ***"
    assert mask_token("nothing to hide", "") == "nothing to hide"


def test_good_run_has_no_problems() -> None:
    assert cli_output_problems(CliResult(0, _GOOD_OUTPUT)) == []


def test_exit_code_and_failure_line_are_reported() -> None:
    output = _GOOD_OUTPUT + "Failed to upload files: can't get data file config!\n"
    problems = cli_output_problems(CliResult(1, output))
    assert "CLI exit code 1" in problems
    assert "CLI output contains 'Failed to upload files'" in problems
    assert "CLI output contains \"can't get data file config\"" in problems


def test_missing_success_lines_are_reported() -> None:
    problems = cli_output_problems(CliResult(0, "Files processed: 3\n"))
    assert "CLI output does not contain 'Files failed: 0'" in problems
    assert "CLI output does not contain 'File uploading completed!'" in problems
    assert "CLI output does not contain 'Files copied:'" in problems


def test_empty_output_is_reported() -> None:
    assert cli_output_problems(CliResult(0, "  \n")) == ["CLI output is empty"]


def test_last_validation_progress_must_be_complete() -> None:
    output = _GOOD_OUTPUT + "2 out of 5 file(s) have been validated.\n"
    assert cli_output_problems(CliResult(0, output)) == ["CLI validated 2 out of 5 files (last progress line)"]


def test_vendored_cli_is_present() -> None:
    assert (cli_dir() / "src" / "uploader.py").is_file()


def test_run_uploader_without_cli_raises(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="Upload CLI not found"):
        run_uploader({"Config": {"token": "t"}}, tmp_path / "work", root=tmp_path)
