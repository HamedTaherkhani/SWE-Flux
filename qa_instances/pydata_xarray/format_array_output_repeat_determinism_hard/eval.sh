#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="format_array_output_repeat_determinism_hard"
TEST_ID="xarray/tests/qa/format_array_output_repeat_determinism_hard_test.py"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"
SOURCE_FILE="$ROOT_DIR/xarray/core/formatting.py"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

if [[ ! -f "$SOURCE_FILE" ]]; then
  echo "ERROR: Missing source file: $SOURCE_FILE"
  exit 1
fi

export TRACE_ON="1"
export TRACE_FILE="xarray/core/formatting.py"
export TRACE_FUNC=""
export TRACE_EVENTS="line"
export TRACE_LOG_ALL_LINES="1"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="220000"
export TRACE_MAXLOCALS="350"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python xarray/tests/qa/parse_format_array_output_repeat_determinism_hard_oracle.py \
  --trace-log "$TRACE_LOG" \
  --source-file "$SOURCE_FILE" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
