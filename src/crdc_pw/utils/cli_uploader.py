"""Run the vendored CRDC Data Hub upload CLI (Katalon CliUploader.uploadFilesViaCli).

The CLI is the Python source in tools/crdc-datahub-cli-uploader (see its VENDORED.md). It needs
Python 3.13 or newer and the `cli` extra (pip install -e ".[cli]"). This module only builds the
YAML config, starts the process and reads its output. It does not touch the browser.

The CLI writes its logs, report and md5 cache into ./tmp relative to its working directory, so the
caller passes a throw-away work_dir (the pytest tmp_path) and the vendored folder stays clean.
The config file holds the API token, so it lives in work_dir and is deleted after the run, and the
token is masked in any output this module returns.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from crdc_pw.locators.loader import repo_root

log = logging.getLogger("crdc_pw.cli_uploader")

TOOL_RELATIVE = Path("tools") / "crdc-datahub-cli-uploader"
UPLOADER_SCRIPT = Path("src") / "uploader.py"
DEFAULT_TIMEOUT_MINUTES = 30

TYPE_DATA_FILE = "data file"
TYPE_METADATA = "metadata"

# The CLI can exit 0 and still log one of these (Katalon: "treat output as source of truth").
FAILURE_MARKERS = ("Failed to upload files", "can't get data file config")

# A good run prints all of these (Katalon verifyCliUploadOutput, which only warned).
REQUIRED_OUTPUT = ("Files failed: 0", "File uploading completed!", "Files processed:", "Files copied:")

_VALIDATED_PROGRESS = re.compile(r"(\d+) out of (\d+) file\(s\) have been validated")


@dataclass(frozen=True)
class CliResult:
    """Exit code and combined stdout/stderr of one uploader run (token already masked)."""

    exit_code: int
    output: str


def cli_dir(root: Path | None = None) -> Path:
    """Folder that holds the vendored CLI (tools/crdc-datahub-cli-uploader)."""
    return (root or repo_root()) / TOOL_RELATIVE


def build_config(
    *,
    api_url: str,
    token: str,
    submission_id: str,
    upload_type: str,
    data_dir: Path,
    manifest: Path | None = None,
    retries: int = 3,
    overwrite: bool = False,
    dryrun: bool = False,
) -> dict[str, Any]:
    """CLI config as a dict with the top-level Config key the CLI reads.

    upload_type is "data file" or "metadata". The manifest is only used for "data file".
    """
    if upload_type not in (TYPE_DATA_FILE, TYPE_METADATA):
        raise ValueError(f"upload_type must be {TYPE_DATA_FILE!r} or {TYPE_METADATA!r}, got {upload_type!r}")
    if upload_type == TYPE_DATA_FILE and manifest is None:
        raise ValueError("A manifest is required for upload type 'data file'")
    config: dict[str, Any] = {
        "api-url": api_url,
        "token": token,
        "submission": submission_id,
        "type": upload_type,
        "data": str(Path(data_dir).resolve()),
    }
    if upload_type == TYPE_DATA_FILE and manifest is not None:
        config["manifest"] = str(Path(manifest).resolve())
    config["retries"] = retries
    config["overwrite"] = overwrite
    config["dryrun"] = dryrun
    return {"Config": config}


def write_config_file(config: dict[str, Any], folder: Path) -> Path:
    """Write the config YAML into folder with owner-only permissions and return its path."""
    path = Path(folder) / "uploader-config.yml"
    path.write_text(yaml.safe_dump(config, default_flow_style=False, sort_keys=False), encoding="utf-8")
    path.chmod(0o600)
    return path


def mask_token(text: str, token: str) -> str:
    """Replace every copy of the token in text, so output can be logged or put in an assertion."""
    if not token:
        return text
    return text.replace(token, "***")


def run_uploader(
    config: dict[str, Any],
    work_dir: Path,
    *,
    timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES,
    root: Path | None = None,
) -> CliResult:
    """Run `python src/uploader.py --config <file>` in work_dir and return exit code and output.

    Raises AssertionError when the CLI folder is missing or the run times out.
    """
    cli_root = cli_dir(root)
    script = cli_root / UPLOADER_SCRIPT
    if not script.is_file():
        raise AssertionError(f"Upload CLI not found at {script}. See tools/crdc-datahub-cli-uploader/VENDORED.md")
    token = str(config.get("Config", {}).get("token", ""))
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    config_path = write_config_file(config, work_dir)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    command = [sys.executable, str(script), "--config", str(config_path)]
    log.info("Running upload CLI: %s (work dir %s)", " ".join(command), work_dir)
    try:
        completed = subprocess.run(
            command,
            cwd=work_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_minutes * 60,
        )
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        raise AssertionError(
            f"Upload CLI timed out after {timeout_minutes} minutes. Output:\n{mask_token(partial, token)}"
        ) from exc
    finally:
        config_path.unlink(missing_ok=True)
    output = mask_token(completed.stdout or "", token)
    log.info("Upload CLI exit code %s. Output:\n%s", completed.returncode, output)
    return CliResult(exit_code=completed.returncode, output=output)


def cli_output_problems(result: CliResult) -> list[str]:
    """What is wrong with a CLI run that was meant to succeed; empty means it is fine.

    Checks the exit code, the failure lines the CLI prints even when it exits 0, the success lines
    (Katalon only warned about these), and that the last "X out of Y file(s) have been validated"
    line shows X equal to Y.
    """
    problems: list[str] = []
    if result.exit_code != 0:
        problems.append(f"CLI exit code {result.exit_code}")
    if not result.output.strip():
        problems.append("CLI output is empty")
        return problems
    for marker in FAILURE_MARKERS:
        if marker in result.output:
            problems.append(f"CLI output contains {marker!r}")
    for text in REQUIRED_OUTPUT:
        if text not in result.output:
            problems.append(f"CLI output does not contain {text!r}")
    progress = _VALIDATED_PROGRESS.findall(result.output)
    if progress:
        done, total = progress[-1]
        if done != total:
            problems.append(f"CLI validated {done} out of {total} files (last progress line)")
    return problems
