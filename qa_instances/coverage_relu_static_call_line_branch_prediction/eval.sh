#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="coverage_relu_static_call_line_branch_prediction"
TEST_ID="keras/src/test/activations/relu_static_call_coverage_prediction_test.py::ReLUStaticCallCoveragePredictionQATest"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

PYTEST_LOG="$LOG_DIR/pytest.log"
COV_JSON="$LOG_DIR/coverage.json"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

rm -f .coverage "$PYTEST_LOG" "$COV_JSON" "$ORACLE_LOG" "$ORACLE_JSON"

coverage erase
coverage run --branch -m pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
coverage json -o "$COV_JSON" >/dev/null

python keras/src/test/parse_coverage_relu_static_call_oracle.py \
  --coverage-json "$COV_JSON" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:      $INSTANCE_ID"
echo "Pytest log:    $PYTEST_LOG"
echo "Coverage json: $COV_JSON"
echo "Oracle log:    $ORACLE_LOG"
echo "Oracle json:   $ORACLE_JSON"
