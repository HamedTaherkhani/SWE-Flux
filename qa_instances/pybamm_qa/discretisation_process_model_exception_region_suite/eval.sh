#!/bin/bash
set -euo pipefail
ROOT_DIR="${1:-/testbed}"; ID="discretisation_process_model_exception_region_suite"; LOG="$ROOT_DIR/logs/qa_instances/$ID"
mkdir -p "$LOG"; cd "$ROOT_DIR"; export PYBAMM_DISABLE_TELEMETRY=true
rm -f "$LOG/pytest.log" "$LOG/report.xml" "$LOG/oracle.log" "$LOG/oracle.json"
set +e
pytest -n 0 -rA -s --tb=short --junitxml="$LOG/report.xml" tests/qa/discretisation_process_model_exception_region_suite_test.py 2>&1 | tee "$LOG/pytest.log"
STATUS=${PIPESTATUS[0]}
set -e
if [[ "$STATUS" -eq 0 ]]; then echo "ERROR: expected crashing tests"; exit 1; fi
python tests/qa/parse_discretisation_process_model_exception_region_suite_oracle.py --report "$LOG/report.xml" --out "$LOG/oracle.json" | tee "$LOG/oracle.log"
