#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="decompose_interp_nth_iteration_state"
TEST_ID="xarray/tests/qa/decompose_interp_nth_iteration_state_test.py::TestDecomposeInterpNthIterationStateHardQA::test_decompose_interp_nth_iteration_state_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="xarray.core.missing.decompose_interp"
export TRACE_EVENTS="line"
export TRACE_LOG_ALL_LINES="1"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="100000"
export TRACE_MAXLOCALS="250"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python xarray/tests/qa/parse_decompose_interp_nth_iteration_state_oracle.py \
  --trace-log "$TRACE_LOG" \
  --source-file "$ROOT_DIR/xarray/core/missing.py" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
