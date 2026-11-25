#!/usr/bin/env bash
# Run one CRDC suite the way the Katalon suite runs: suite setup first, then the suite, serially.
#
#   CRDC_PROFILE=qa2 bash ci/run_suite.sh [marker] [extra pytest args]
#
# marker defaults to CRDC_Smoke (any marker in pytest.ini works, for example CRDC_Regression).
# Extra arguments go to the suite run only, not to the setup or restore runs.
#
# 1. Setup: EnableAllPermissions (the Katalon suite setup). It must run and pass: a skipped test
#    (for example Master credentials missing in the profile yaml) exits 0 in pytest, so the JUnit
#    file is checked. If setup fails the script stops; the suite would only report misleading
#    permission failures.
# 2. Suite: pytest -m <marker>.
# 3. Restore: EnableAllPermissions again after the suite, even when the suite failed, because
#    some suites (CRDC_Regression: PBAC TC11 to TC15) leave shared users' permissions unchecked.
#    The one exception is a plain "CRDC_PBAC" run with no extra arguments: that suite already ends
#    with EnableAllPermissions. Any extra argument (for example -k TC11, which does not collect
#    EnableAllPermissions, or -x, which can stop the run before it) brings the restore back.
#
# Every run is serial, has tracing off and writes its JUnit file to a fixed path: those options
# come after the caller's arguments (and after PYTEST_ADDOPTS) so they cannot be overridden (a
# trace holds the Hub tab's network requests and this repo is public; PBAC cases share
# permissions, so no parallel runs). JUnit XML goes under reports/ (junit-setup.xml, junit.xml,
# junit-restore.xml).
#
# Exit code: the suite's pytest exit code when it is not 0; otherwise 1 if the restore failed;
# otherwise 0.
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

marker="${1:-CRDC_Smoke}"
if [ "$#" -gt 0 ]; then
  shift
fi

# A plain CRDC_PBAC run already ends with EnableAllPermissions; every other run needs the restore.
restore_needed=1
if [ "${marker}" = "CRDC_PBAC" ] && [ "$#" -eq 0 ]; then
  restore_needed=0
fi

FORCED=(--tracing=off -n 0)

mkdir -p reports

# Succeeds only when the JUnit file has exactly one test case and it ran and passed.
check_permissions_junit() {
  python - "$1" <<'PY'
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
try:
    cases = ET.parse(path).getroot().findall(".//testcase")
except (OSError, ET.ParseError) as exc:
    sys.exit(f"Cannot read {path}: {exc}")
if len(cases) != 1:
    sys.exit(f"Expected exactly 1 EnableAllPermissions test in {path}, found {len(cases)}")
case = cases[0]
for tag in ("skipped", "failure", "error"):
    if case.find(tag) is not None:
        sys.exit(f"EnableAllPermissions did not pass ({tag}) in {path}; see the pytest output above")
PY
}

# Runs EnableAllPermissions and checks the result. $1 is the JUnit file name under reports/.
enable_all_permissions() {
  python -m pytest -m CRDC_PBAC -k EnableAllPermissions --junitxml="reports/$1" "${FORCED[@]}" || return $?
  check_permissions_junit "reports/$1"
}

echo "Profile: ${CRDC_PROFILE:-qa}  Suite marker: ${marker}"

echo "== Suite setup: EnableAllPermissions =="
if ! enable_all_permissions junit-setup.xml; then
  echo "Suite setup failed; not running the suite." >&2
  exit 1
fi

echo "== Suite: ${marker} =="
python -m pytest -m "${marker}" "$@" --junitxml=reports/junit.xml "${FORCED[@]}"
suite_rc=$?

restore_rc=0
if [ "${restore_needed}" -eq 1 ]; then
  echo "== Restore: EnableAllPermissions =="
  if ! enable_all_permissions junit-restore.xml; then
    echo "Restoring permissions after the suite FAILED; shared users may be left with unchecked permissions." >&2
    restore_rc=1
  fi
fi

if [ "${suite_rc}" -ne 0 ]; then
  exit "${suite_rc}"
fi
exit "${restore_rc}"
