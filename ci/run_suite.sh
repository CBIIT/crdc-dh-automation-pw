#!/usr/bin/env bash
# Run one CRDC suite the way the Katalon suite runs: suite setup first, then the suite, serially.
#
#   CRDC_PROFILE=qa2 bash ci/run_suite.sh [marker] [extra pytest args]
#
# marker defaults to CRDC_Smoke (any marker in pytest.ini works, for example CRDC_Regression).
# Extra arguments go to the suite run only, not to the setup run.
#
# 1. EnableAllPermissions (the Katalon suite setup). If it fails the script stops: the suite
#    would only report misleading permission failures.
# 2. pytest -m <marker>, serial (PBAC cases share permissions, so never add -n here).
#
# Both runs pass --tracing=off (a trace holds the Hub tab's network requests and this repo is
# public) and write JUnit XML under reports/ (junit-setup.xml and junit.xml). The script exits
# with the suite's pytest exit code.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

marker="${1:-CRDC_Smoke}"
if [ "$#" -gt 0 ]; then
  shift
fi

mkdir -p reports

echo "Profile: ${CRDC_PROFILE:-qa}  Suite marker: ${marker}"

echo "== Suite setup: EnableAllPermissions =="
python -m pytest -m CRDC_PBAC -k EnableAllPermissions --tracing=off --junitxml=reports/junit-setup.xml

echo "== Suite: ${marker} =="
python -m pytest -m "${marker}" --tracing=off --junitxml=reports/junit.xml "$@"
