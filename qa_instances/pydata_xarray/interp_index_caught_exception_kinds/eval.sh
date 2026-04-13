#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="interp_index_caught_exception_kinds"
TEST_ID="xarray/tests/qa/interp_index_caught_exception_kinds_test.py::TestInterpIndexCaughtExceptionKindsHardQA::test_interp_index_caught_exception_kinds_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="xarray/core/missing.py"
export TRACE_FUNC="xarray.core.missing.get_clean_interp_index"
export TRACE_EVENTS="exception"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="400"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python xarray/tests/qa/parse_interp_index_caught_exception_kinds_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
