"""Run the vendored CRDC Data Hub upload CLI (Katalon CliUploader.uploadFilesViaCli).

The CLI is the Python source in tools/crdc-datahub-cli-uploader (see its VENDORED.md). It needs
Python 3.13 or newer. Its requirements are installed before every run, as Katalon does (see
ensure_cli_dependencies). This module only builds the YAML config, starts the process and reads its
output. It does not touch the browser.

The CLI writes its logs, report and md5 cache into ./tmp relative to its working directory, so the
run gets its own throw-away work_dir (a new temporary folder unless the caller passes one) and the
vendored folder stays clean.
The data folder in InputFiles is only read. The files the CLI writes beside the manifest
(<manifest>-final.tsv and the -final files of child tsv/txt files) go to a copy in work_dir.
The config file holds the API token, so it lives in work_dir and is deleted after the run, and the
token is masked in any output this module returns.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from crdc_pw.config import Settings
from crdc_pw.hub import Hub
from crdc_pw.locators.loader import repo_root
from crdc_pw.pages.data_submissions_list import parse_submission_id_from_text
from crdc_pw.utils.validation_results import metadata_dir

log = logging.getLogger("crdc_pw.cli_uploader")

TOOL_RELATIVE = Path("tools") / "crdc-datahub-cli-uploader"
UPLOADER_SCRIPT = Path("src") / "uploader.py"
DEFAULT_TIMEOUT_MINUTES = 30
PIP_INSTALL_TIMEOUT_MINUTES = 3

# The CLI needs this Python or newer (its README).
MIN_PYTHON = (3, 13)

TYPE_DATA_FILE = "data file"
TYPE_METADATA = "metadata"

# The CLI can exit 0 and still log one of these (Katalon: "treat output as source of truth").
FAILURE_MARKERS = ("Failed to upload files", "can't get data file config")

# A good run prints all of these (Katalon verifyCliUploadOutput, which only warned).
REQUIRED_OUTPUT = ("Files failed: 0", "File uploading completed!", "Files processed:", "Files copied:")

_VALIDATED_PROGRESS = re.compile(r"(\d+) out of (\d+) file\(s\) have been validated")

# Input folders under InputFiles/CRDC/MetadataData/<tc>/ (Katalon getDataFilesPath and getMetaDataPath).
DATA_FILES_FOLDER = "DataFiles"
METADATA_FOLDER = "Metadata"
ARCHIVE_MANIFEST_NAME = "zip-archive-manifest.tsv"
MANIFEST_SUFFIX = "manifest.tsv"


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
    archive_manifest: Path | None = None,
    id_field: str | None = None,
    retries: int = 3,
    overwrite: bool = False,
    dryrun: bool = False,
) -> dict[str, Any]:
    """CLI config as a dict with the top-level Config key the CLI reads.

    upload_type is "data file" or "metadata". The manifest, archive_manifest (zip files) and
    id_field (manifest column that holds the file id) are only used for "data file".
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
        if archive_manifest is not None:
            config["archive_manifest"] = str(Path(archive_manifest).resolve())
        if id_field:
            config["id-field"] = id_field
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


def _run_python(python: str, args: list[str], *, cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    """Run the interpreter with args and capture stdout and stderr together as text."""
    return subprocess.run(
        [python, *args],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )


def ensure_cli_dependencies(python: str, root: Path | None = None) -> None:
    """Make sure the interpreter can run the CLI: check its version, then install the requirements.

    Like Katalon, `pip install -r requirements.txt --quiet` runs before every CLI run (3 minute
    timeout), so a pipeline needs no separate install step. The version check is added: the CLI
    needs MIN_PYTHON or newer and fails with an unclear error otherwise.
    Raises AssertionError when the interpreter is too old or the install fails or times out.
    """
    cli_root = cli_dir(root)
    version = _run_python(
        python,
        ["-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
        cwd=cli_root,
        timeout_seconds=30,
    ).stdout.strip()
    major, _, minor = version.partition(".")
    if not (major.isdigit() and minor.isdigit()) or (int(major), int(minor)) < MIN_PYTHON:
        need = ".".join(str(part) for part in MIN_PYTHON)
        raise AssertionError(f"The upload CLI needs Python {need} or newer, but {python} is {version or 'unknown'}")
    requirements = cli_root / "requirements.txt"
    log.info("Installing upload CLI requirements from %s with %s", requirements, python)
    try:
        install = _run_python(
            python,
            ["-m", "pip", "install", "-r", str(requirements), "--quiet"],
            cwd=cli_root,
            timeout_seconds=PIP_INSTALL_TIMEOUT_MINUTES * 60,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(
            f"pip install of the upload CLI requirements timed out after {PIP_INSTALL_TIMEOUT_MINUTES} minutes"
        ) from exc
    if install.returncode != 0:
        raise AssertionError(
            f"pip install of the upload CLI requirements failed (exit {install.returncode}):\n{install.stdout}"
        )


def run_uploader(
    config: dict[str, Any],
    work_dir: Path,
    *,
    timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES,
    root: Path | None = None,
) -> CliResult:
    """Run `python src/uploader.py --config <file>` in work_dir and return exit code and output.

    The interpreter is the one running pytest (sys.executable); see ensure_cli_dependencies. Raises AssertionError when the CLI folder is missing or the run times out.
    """
    cli_root = cli_dir(root)
    script = cli_root / UPLOADER_SCRIPT
    if not script.is_file():
        raise AssertionError(f"Upload CLI not found at {script}. See tools/crdc-datahub-cli-uploader/VENDORED.md")
    interpreter = sys.executable
    ensure_cli_dependencies(interpreter, root)
    token = str(config.get("Config", {}).get("token", ""))
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    config_path = write_config_file(config, work_dir)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    command = [interpreter, str(script), "--config", str(config_path)]
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


@dataclass(frozen=True)
class CliOptions:
    """Optional CLI settings from the profile yaml (Katalon CRDC_CLI_* and CRDC_MANIFEST_ID_FIELD)."""

    retries: int = 3
    overwrite: bool = False
    dryrun: bool = False
    id_field: str | None = None


@dataclass(frozen=True)
class CliUpload:
    """One CLI upload.

    data_dir is the input folder the CLI read (InputFiles, not changed). manifest is the copy in
    work_dir that the CLI wrote <manifest>-final.tsv next to (None for metadata). cli_work_dir is
    the CLI's working directory, whose tmp folder holds its upload report and log.
    """

    result: CliResult
    data_dir: Path
    manifest: Path | None
    cli_work_dir: Path


def _as_bool(value: Any) -> bool:
    """YAML bool or text such as "true" or "1" (Katalon accepted both)."""
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("true", "1")


def options_from_settings(settings: Settings) -> CliOptions:
    """Read CRDC_CLI_RETRIES, CRDC_CLI_OVERWRITE, CRDC_CLI_DRYRUN and CRDC_MANIFEST_ID_FIELD.

    All are optional. Katalon defaults apply: 3 retries, no overwrite, no dry run, no id field.
    """
    data = settings.data
    try:
        retries = int(str(data.get("CRDC_CLI_RETRIES") or "3").strip())
    except ValueError:
        retries = 3
    id_field = str(data.get("CRDC_MANIFEST_ID_FIELD") or "").strip() or None
    return CliOptions(
        retries=retries,
        overwrite=_as_bool(data.get("CRDC_CLI_OVERWRITE")),
        dryrun=_as_bool(data.get("CRDC_CLI_DRYRUN")),
        id_field=id_field,
    )


def require_submitter_token(settings: Settings) -> str:
    """The Submitter API token, or AssertionError with a clear message when the profile yaml has none.

    Call it at the start of a CLI test so a missing token fails before any submission is created.
    """
    token = settings.submitter_api_token
    if not token:
        raise AssertionError(
            f"SubmitterApiToken is empty in {settings.config_path.name}. "
            "Add it (from the Katalon profile) so the upload CLI can run."
        )
    return token


def normalize_upload_type(data_type: str) -> str:
    """ "datafile" or "data file" gives the CLI type "data file", "metadata" gives "metadata" (case-insensitive)."""
    text = (data_type or "").strip().lower()
    if text in ("datafile", "data file"):
        return TYPE_DATA_FILE
    if text == "metadata":
        return TYPE_METADATA
    raise ValueError(f"data_type must be 'datafile' or 'metadata', got {data_type!r}")


def find_manifest(data_dir: Path) -> Path:
    """The manifest in a DataFiles folder: manifest.tsv, else the first file ending in manifest.tsv.

    Katalon takes the first file ending in manifest.tsv in whatever order the file system lists them,
    which can also be zip-archive-manifest.tsv. Here that file is skipped and the choice is sorted.
    """
    candidates = sorted(
        path
        for path in Path(data_dir).iterdir()
        if path.is_file() and path.name.lower().endswith(MANIFEST_SUFFIX) and path.name != ARCHIVE_MANIFEST_NAME
    )
    for path in candidates:
        if path.name.lower() == MANIFEST_SUFFIX:
            return path
    if not candidates:
        raise AssertionError(f"No manifest file ending with {MANIFEST_SUFFIX!r} found in: {data_dir}")
    return candidates[0]


def has_zip_files(data_dir: Path) -> bool:
    """True when the folder has at least one .zip file (these need zip-archive-manifest.tsv)."""
    return any(path.is_file() and path.name.lower().endswith(".zip") for path in Path(data_dir).iterdir())


def copy_manifest_folder_files(source: Path, target: Path) -> None:
    """Copy the .tsv and .txt files of source into target, leaving out any old -final files.

    These are the files the CLI reads beside the manifest (the manifest, the archive manifest and
    child metadata files that get a file id) and the only place it writes next to. Data files are
    not copied. Katalon runs in InputFiles itself and deletes the stale -final.tsv first; a fresh
    copy without the -final files has the same effect.
    """
    target.mkdir(parents=True)
    for path in sorted(source.iterdir()):
        if path.is_file() and path.suffix.lower() in (".tsv", ".txt") and "-final." not in path.name:
            shutil.copy2(path, target / path.name)


def _input_dir(tc_name: str, upload_type: str) -> Path:
    """InputFiles/CRDC/MetadataData/<tc>/DataFiles or /Metadata; fails when the folder is missing."""
    folder = DATA_FILES_FOLDER if upload_type == TYPE_DATA_FILE else METADATA_FOLDER
    data_dir = metadata_dir(tc_name) / folder
    if not data_dir.is_dir():
        raise AssertionError(f"Upload CLI input folder not found or not a directory: {data_dir}")
    return data_dir


def _prepare_manifests(
    data_dir: Path, work_dir: Path, *, expect_validation_errors: bool, omit_archive_manifest: bool
) -> tuple[Path, Path | None]:
    """Copy the manifest folder's tsv and txt files to work_dir/manifest; return (manifest, archive manifest).

    The archive manifest is None without .zip files. With .zip files it is required, except when
    expect_validation_errors and omit_archive_manifest are both set (the CLI then reports it missing).
    """
    manifest_dir = work_dir / "manifest"
    copy_manifest_folder_files(data_dir, manifest_dir)
    manifest = manifest_dir / find_manifest(data_dir).name
    if not has_zip_files(data_dir):
        return manifest, None
    if expect_validation_errors and omit_archive_manifest:
        log.info("Leaving out the archive manifest so the CLI reports it missing")
        return manifest, None
    archive_manifest = manifest_dir / ARCHIVE_MANIFEST_NAME
    if not archive_manifest.is_file():
        # Katalon fails here too, even with expect_validation_errors: the only way to run zip files
        # without it is to ask for that (omit_archive_manifest together with expect_validation_errors).
        raise AssertionError(f"{ARCHIVE_MANIFEST_NAME} is required when uploading .zip files: {data_dir}")
    return manifest, archive_manifest


def upload_files_via_cli(
    hub: Hub,
    tc_name: str,
    data_type: str,
    *,
    expect_validation_errors: bool = False,
    omit_archive_manifest: bool = False,
    work_dir: Path | None = None,
) -> CliUpload:
    """Upload a test case's input files with the CLI (Katalon uploadFilesViaCli).

    Like Katalon, the submission is the one the browser is on: its id is read from the current URL,
    so open the submission (as the test does after creating it) before calling. The API URL, token
    and CLI options come from hub.settings.

    data_type "datafile" uploads InputFiles/CRDC/MetadataData/<tc>/DataFiles with its manifest;
    "metadata" uploads <tc>/Metadata. The CLI reads the data files straight from InputFiles, which
    it never writes to. For a data file upload the manifest folder's tsv and txt files are copied to
    <work dir>/manifest (copy_manifest_folder_files) and the CLI is given that manifest, so its
    <manifest>-final.tsv lands there and not in InputFiles.

    work_dir is where the copy and the CLI's own tmp folder (upload report and log) go. Leave it out
    and every call gets a new temporary folder, so two uploads in one test never share files. A
    folder you pass must be new for each call. The returned CliUpload says where everything is.

    With .zip files in a data file upload, zip-archive-manifest.tsv is required and passed on, except
    when expect_validation_errors and omit_archive_manifest are both set, which leaves it out so the
    CLI reports the missing archive manifest (see _prepare_manifests).

    By default the run must succeed (see cli_output_problems) or this raises AssertionError. With
    expect_validation_errors the CLI output is returned unchecked, for tests that assert the error
    messages themselves (verify_cli_error_messages). Katalon also refreshes the page after the
    upload; callers that look at the UI afterwards should reload it.
    """
    settings = hub.settings
    upload_type = normalize_upload_type(data_type)
    token = require_submitter_token(settings)
    submission_id = parse_submission_id_from_text(hub.page.url)
    if not submission_id:
        raise AssertionError(f"Upload CLI needs a submission id in the page URL, got {hub.page.url!r}")
    log.info("Submission ID: %s", submission_id)
    data_dir = _input_dir(tc_name, upload_type)
    work_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="crdc-cli-"))

    manifest: Path | None = None
    archive_manifest: Path | None = None
    if upload_type == TYPE_DATA_FILE:
        manifest, archive_manifest = _prepare_manifests(
            data_dir,
            work_dir,
            expect_validation_errors=expect_validation_errors,
            omit_archive_manifest=omit_archive_manifest,
        )

    options = options_from_settings(settings)
    config = build_config(
        api_url=settings.api_url,
        token=token,
        submission_id=submission_id,
        upload_type=upload_type,
        data_dir=data_dir,
        manifest=manifest,
        archive_manifest=archive_manifest,
        id_field=options.id_field,
        retries=options.retries,
        overwrite=options.overwrite,
        dryrun=options.dryrun,
    )
    cli_work_dir = work_dir / "cli"
    result = run_uploader(config, cli_work_dir)
    if not expect_validation_errors:
        problems = cli_output_problems(result)
        assert not problems, "CLI upload problems:\n" + "\n".join(problems) + f"\nOutput:\n{result.output}"
        log.info("Assert CLI upload succeeded")
    return CliUpload(result=result, data_dir=data_dir, manifest=manifest, cli_work_dir=cli_work_dir)
