"""No-browser checks for the upload CLI runner (CRDCDH-1405 TC101). The CLI itself is not run.

Flow (this file):
  1. build_config for data file and metadata, and its validation
  2. write_config_file holds the token with owner-only permissions
  3. mask_token
  4. cli_output_problems: good run, failure lines, missing lines, validation progress
  5. run_uploader raises when the CLI folder is missing
  6. Options from the profile yaml, upload type, manifest and zip handling
  7. upload_files_via_cli copies the manifest files, builds the config, and checks the run (run_uploader is faked)
  8. ensure_cli_dependencies checks the Python version and installs the requirements on every call
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

import pytest
import yaml

import crdc_pw.pages.cli_uploader as cli_uploader
from crdc_pw.config import Settings
from crdc_pw.pages.cli_uploader import (
    TYPE_DATA_FILE,
    TYPE_METADATA,
    CliOptions,
    CliResult,
    build_config,
    cli_dir,
    cli_output_problems,
    ensure_cli_dependencies,
    find_manifest,
    has_zip_files,
    mask_token,
    normalize_upload_type,
    options_from_settings,
    require_submitter_token,
    run_uploader,
    upload_files_via_cli,
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


def _settings(**data: object) -> Settings:
    return Settings(
        profile="qa",
        base_url="https://hub-qa.datacommons.cancer.gov/",
        config_path=Path("qa.yaml"),
        data=dict(data),
    )


def test_build_config_adds_archive_manifest_and_id_field_for_data_file(tmp_path: Path) -> None:
    config = build_config(
        api_url="u",
        token="t",
        submission_id="s",
        upload_type=TYPE_DATA_FILE,
        data_dir=tmp_path,
        manifest=tmp_path / "manifest.tsv",
        archive_manifest=tmp_path / "zip-archive-manifest.tsv",
        id_field="my_id",
        retries=5,
        overwrite=True,
        dryrun=True,
    )["Config"]
    assert config["archive_manifest"] == str((tmp_path / "zip-archive-manifest.tsv").resolve())
    assert config["id-field"] == "my_id"
    assert (config["retries"], config["overwrite"], config["dryrun"]) == (5, True, True)


def test_build_config_leaves_out_archive_manifest_and_id_field_for_metadata(tmp_path: Path) -> None:
    config = build_config(
        api_url="u",
        token="t",
        submission_id="s",
        upload_type=TYPE_METADATA,
        data_dir=tmp_path,
        archive_manifest=tmp_path / "zip-archive-manifest.tsv",
        id_field="my_id",
    )["Config"]
    assert "archive_manifest" not in config and "id-field" not in config


def test_options_default_and_from_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRDC_CLI_PYTHON", raising=False)
    assert options_from_settings(_settings()) == CliOptions(3, False, False, None, None)
    options = options_from_settings(
        _settings(
            CRDC_CLI_RETRIES="5",
            CRDC_CLI_OVERWRITE="true",
            CRDC_CLI_DRYRUN=True,
            CRDC_MANIFEST_ID_FIELD=" my_id ",
            CRDC_CLI_PYTHON=" /usr/bin/python3.13 ",
        )
    )
    assert options == CliOptions(5, True, True, "my_id", "/usr/bin/python3.13")
    assert options_from_settings(_settings(CRDC_CLI_RETRIES="many")).retries == 3


def test_options_python_falls_back_to_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRDC_CLI_PYTHON", "/opt/py313/bin/python")
    assert options_from_settings(_settings()).python == "/opt/py313/bin/python"
    assert options_from_settings(_settings(CRDC_CLI_PYTHON="/yaml/python")).python == "/yaml/python"


def test_normalize_upload_type() -> None:
    assert normalize_upload_type("datafile") == TYPE_DATA_FILE
    assert normalize_upload_type(" Data File ") == TYPE_DATA_FILE
    assert normalize_upload_type("METADATA") == TYPE_METADATA
    with pytest.raises(ValueError):
        normalize_upload_type("zip")


def test_require_submitter_token() -> None:
    assert require_submitter_token(_settings(SubmitterApiToken="tok")) == "tok"
    with pytest.raises(AssertionError, match="SubmitterApiToken is empty in qa.yaml"):
        require_submitter_token(_settings())


def test_find_manifest_prefers_manifest_tsv_and_skips_archive_manifest(tmp_path: Path) -> None:
    for name in ("zip-archive-manifest.tsv", "a-manifest.tsv", "manifest.tsv", "demo.txt"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert find_manifest(tmp_path).name == "manifest.tsv"
    (tmp_path / "manifest.tsv").unlink()
    assert find_manifest(tmp_path).name == "a-manifest.tsv"
    (tmp_path / "a-manifest.tsv").unlink()
    with pytest.raises(AssertionError, match="No manifest file"):
        find_manifest(tmp_path)


def test_has_zip_files(tmp_path: Path) -> None:
    assert not has_zip_files(tmp_path)
    (tmp_path / "A.ZIP").write_text("x", encoding="utf-8")
    assert has_zip_files(tmp_path)


def _input_folder(root: Path, tc: str, folder: str, files: dict[str, str]) -> Path:
    path = root / "InputFiles" / "CRDC" / "MetadataData" / tc / folder
    path.mkdir(parents=True)
    for name, text in files.items():
        (path / name).write_text(text, encoding="utf-8")
    return path


class _FakeRun:
    """Stands in for run_uploader and records what it was given."""

    def __init__(self, result: CliResult) -> None:
        self.result = result
        self.configs: list[dict] = []
        self.work_dirs: list[Path] = []
        self.pythons: list[str | None] = []

    def __call__(self, config: dict, work_dir: Path, **kwargs: object) -> CliResult:
        self.configs.append(config["Config"])
        self.work_dirs.append(work_dir)
        self.pythons.append(kwargs.get("python"))  # type: ignore[arg-type]
        return self.result


def test_upload_data_files_leaves_inputs_alone_and_copies_manifest_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CRDC_CLI_PYTHON", raising=False)
    source = _input_folder(
        tmp_path,
        "TC",
        "DataFiles",
        {
            "manifest.tsv": "type\tfile_name\n",
            "child.txt": "c",
            "old-manifest-final.tsv": "stale",
            "demo.csv": "x",
            "demo.pdf": "x",
        },
    )
    fake = _FakeRun(CliResult(0, _GOOD_OUTPUT))
    monkeypatch.setattr(cli_uploader, "run_uploader", fake)
    settings = _settings(SubmitterApiToken="tok", ApiUrl="https://hub/api/graphql", CRDC_MANIFEST_ID_FIELD="my_id")

    upload = upload_files_via_cli(settings, "sub-1", "TC", "datafile", tmp_path / "run", root=tmp_path)

    config = fake.configs[0]
    manifest_dir = tmp_path / "run" / "manifest"
    assert upload.data_dir == source and upload.manifest == manifest_dir / "manifest.tsv"
    assert upload.cli_work_dir == tmp_path / "run" / "cli"
    assert config["api-url"] == "https://hub/api/graphql" and config["token"] == "tok"
    assert config["submission"] == "sub-1" and config["type"] == "data file"
    assert config["data"] == str(source.resolve())
    assert config["manifest"] == str(upload.manifest.resolve()) and config["id-field"] == "my_id"
    assert "archive_manifest" not in config
    assert fake.work_dirs == [upload.cli_work_dir] and fake.pythons == [None]
    # only tsv and txt files are copied, never an old -final file or a data file
    assert sorted(path.name for path in manifest_dir.iterdir()) == ["child.txt", "manifest.tsv"]
    assert sorted(path.name for path in source.iterdir()) == [
        "child.txt",
        "demo.csv",
        "demo.pdf",
        "manifest.tsv",
        "old-manifest-final.tsv",
    ]


def test_upload_passes_configured_python_to_the_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _input_folder(tmp_path, "TC", "DataFiles", {"manifest.tsv": "x"})
    fake = _FakeRun(CliResult(0, _GOOD_OUTPUT))
    monkeypatch.setattr(cli_uploader, "run_uploader", fake)
    upload_files_via_cli(
        _settings(SubmitterApiToken="tok", CRDC_CLI_PYTHON="/opt/py313/bin/python"),
        "sub-1",
        "TC",
        "datafile",
        tmp_path / "run",
        root=tmp_path,
    )
    assert fake.pythons == ["/opt/py313/bin/python"]


def test_upload_metadata_uses_metadata_folder_without_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _input_folder(tmp_path, "TC", "Metadata", {"GC_study.tsv": "type\tid\n"})
    fake = _FakeRun(CliResult(0, _GOOD_OUTPUT))
    monkeypatch.setattr(cli_uploader, "run_uploader", fake)
    upload = upload_files_via_cli(
        _settings(SubmitterApiToken="tok"), "sub-1", "TC", "metadata", tmp_path / "run", root=tmp_path
    )
    assert upload.manifest is None and upload.data_dir.name == "Metadata"
    assert not (tmp_path / "run" / "manifest").exists()
    assert fake.configs[0]["type"] == "metadata" and "manifest" not in fake.configs[0]


def test_upload_failed_run_raises_with_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _input_folder(tmp_path, "TC", "DataFiles", {"manifest.tsv": "x"})
    monkeypatch.setattr(cli_uploader, "run_uploader", _FakeRun(CliResult(0, "Failed to upload files: nope")))
    with pytest.raises(AssertionError, match="CLI upload problems"):
        upload_files_via_cli(
            _settings(SubmitterApiToken="tok"), "sub-1", "TC", "datafile", tmp_path / "run", root=tmp_path
        )


def test_upload_expect_validation_errors_returns_unchecked_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _input_folder(tmp_path, "TC", "DataFiles", {"manifest.tsv": "x"})
    monkeypatch.setattr(cli_uploader, "run_uploader", _FakeRun(CliResult(1, "found invalid file(s)")))
    upload = upload_files_via_cli(
        _settings(SubmitterApiToken="tok"),
        "sub-1",
        "TC",
        "datafile",
        tmp_path / "run",
        expect_validation_errors=True,
        root=tmp_path,
    )
    assert upload.result.exit_code == 1


def test_upload_zip_files_need_archive_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _input_folder(tmp_path, "TC", "DataFiles", {"manifest.tsv": "x", "a.zip": "z"})
    fake = _FakeRun(CliResult(0, _GOOD_OUTPUT))
    monkeypatch.setattr(cli_uploader, "run_uploader", fake)
    settings = _settings(SubmitterApiToken="tok")
    with pytest.raises(AssertionError, match="zip-archive-manifest.tsv is required"):
        upload_files_via_cli(settings, "sub-1", "TC", "datafile", tmp_path / "run1", root=tmp_path)

    (source / "zip-archive-manifest.tsv").write_text("x", encoding="utf-8")
    upload = upload_files_via_cli(settings, "sub-1", "TC", "datafile", tmp_path / "run2", root=tmp_path)
    manifest_dir = tmp_path / "run2" / "manifest"
    assert fake.configs[-1]["archive_manifest"] == str((manifest_dir / "zip-archive-manifest.tsv").resolve())
    assert fake.configs[-1]["data"] == str(source.resolve())
    assert upload.manifest is not None and upload.manifest.name == "manifest.tsv"


def test_upload_can_leave_out_archive_manifest_when_errors_are_expected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _input_folder(tmp_path, "TC", "DataFiles", {"manifest.tsv": "x", "a.zip": "z", "zip-archive-manifest.tsv": "x"})
    fake = _FakeRun(CliResult(1, "No archive manifest found for a.zip"))
    monkeypatch.setattr(cli_uploader, "run_uploader", fake)
    upload_files_via_cli(
        _settings(SubmitterApiToken="tok"),
        "sub-1",
        "TC",
        "datafile",
        tmp_path / "run",
        expect_validation_errors=True,
        omit_archive_manifest=True,
        root=tmp_path,
    )
    assert "archive_manifest" not in fake.configs[0]


def test_upload_missing_token_folder_and_submission_id_raise(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="SubmitterApiToken is empty"):
        upload_files_via_cli(_settings(), "sub-1", "TC", "datafile", tmp_path / "run", root=tmp_path)
    settings = _settings(SubmitterApiToken="tok")
    with pytest.raises(AssertionError, match="submission id"):
        upload_files_via_cli(settings, "", "TC", "datafile", tmp_path / "run", root=tmp_path)
    with pytest.raises(AssertionError, match="input folder not found"):
        upload_files_via_cli(settings, "sub-1", "TC", "datafile", tmp_path / "run", root=tmp_path)


class _FakeInterpreter:
    """Stands in for _run_python: answers the version probe and pip install."""

    def __init__(self, version: str = "3.13", pip_exit: int = 0) -> None:
        self.version = version
        self.pip_exit = pip_exit
        self.calls: list[list[str]] = []

    def __call__(self, python: str, args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[0] == "-c":
            return subprocess.CompletedProcess(args, 0, stdout=self.version + "\n")
        return subprocess.CompletedProcess(args, self.pip_exit, stdout="pip output")


def test_requirements_are_installed_on_every_call(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeInterpreter()
    monkeypatch.setattr(cli_uploader, "_run_python", fake)
    ensure_cli_dependencies("py")
    ensure_cli_dependencies("py")
    install = [call for call in fake.calls if call[:2] == ["-m", "pip"]]
    assert len(install) == 2 and install[0][2:4] == ["install", "-r"]
    assert install[0][4].endswith("requirements.txt") and install[0][-1] == "--quiet"


def test_failed_install_raises_with_pip_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_uploader, "_run_python", _FakeInterpreter(pip_exit=1))
    with pytest.raises(AssertionError, match="(?s)pip install of the upload CLI requirements failed.*pip output"):
        ensure_cli_dependencies("py")


def test_install_timeout_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def slow(python: str, args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[0] == "-c":
            return subprocess.CompletedProcess(args, 0, stdout="3.13\n")
        raise subprocess.TimeoutExpired(args, 180)

    monkeypatch.setattr(cli_uploader, "_run_python", slow)
    with pytest.raises(AssertionError, match="timed out after 3 minutes"):
        ensure_cli_dependencies("py")


def test_old_python_is_rejected_before_any_install(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeInterpreter(version="3.11")
    monkeypatch.setattr(cli_uploader, "_run_python", fake)
    with pytest.raises(AssertionError, match="needs Python 3.13 or newer, but py is 3.11"):
        ensure_cli_dependencies("py")
    assert len(fake.calls) == 1
