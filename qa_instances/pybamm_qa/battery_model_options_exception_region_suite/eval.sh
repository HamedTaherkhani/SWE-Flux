#!/bin/bash
set -euo pipefail
ROOT_DIR="${1:-/testbed}"
ID="battery_model_options_exception_region_suite"
LOG="$ROOT_DIR/logs/qa_instances/$ID"
mkdir -p "$LOG"
cd "$ROOT_DIR"
export PYBAMM_DISABLE_TELEMETRY=true
rm -f "$LOG/pytest.log" "$LOG/report.xml" "$LOG/oracle.log" "$LOG/oracle.json"
set +e
pytest -n 0 -rA -s --tb=short \
  --junitxml="$LOG/report.xml" \
  tests/qa/battery_model_options_exception_region_suite_test.py \
  2>&1 | tee "$LOG/pytest.log"
PYTEST_STATUS=${PIPESTATUS[0]}
set -e
if [[ "$PYTEST_STATUS" -eq 0 ]]; then
  echo "ERROR: expected this exceptional-behavior suite to contain crashing tests"
  exit 1
fi
python tests/qa/parse_battery_model_options_exception_region_suite_oracle.py \
  --report "$LOG/report.xml" --out "$LOG/oracle.json" | tee "$LOG/oracle.log"
