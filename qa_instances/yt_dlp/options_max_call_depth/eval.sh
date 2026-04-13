#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="options_max_call_depth"
TEST_ID="test/qa/options_max_call_depth_test.py::TestOptionsMaxCallDepthQA::test_options_max_call_depth_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"
SOURCE_FILE="$ROOT_DIR/yt_dlp/options.py"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

if [[ ! -f "$SOURCE_FILE" ]]; then
  echo "ERROR: Missing source file: $SOURCE_FILE"
  exit 1
fi

export TRACE_ON="1"
# Trace only the QA test file so the call-depth is fully determined by the test's
# own call structure (and does not depend on Python/yt_dlp internal call naming).
export TRACE_FILE="test/qa/options_max_call_depth_test.py"
export TRACE_FUNC=""
export TRACE_EVENTS="call,return"
export TRACE_LOG_ALL_LINES="0"
export TRACE_OUT="$TRACE_LOG"
export TRACE_TIME="0"
export TRACE_LIMIT="220000"
export TRACE_MAXLOCALS="120"
export TRACE_FULL_LOCALS_ON_RETURN="0"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python test/qa/parse_options_max_call_depth_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
