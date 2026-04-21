#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="dispatch_process_dynamic_target"
TEST_ID="test/qa/dispatch_process_dynamic_target_test.py::TestDispatchProcessDynamicTargetQA::test_dispatch_process_dynamic_target_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"
SOURCE_FILE="$ROOT_DIR/yt_dlp/dispatching.py"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

if [[ ! -f "$SOURCE_FILE" ]]; then
  echo "ERROR: Missing source file: $SOURCE_FILE"
  exit 1
fi

export TRACE_ON="1"
export TRACE_FILE="yt_dlp/dispatching.py"
export TRACE_FUNC=""
export TRACE_EVENTS="call"
export TRACE_LOG_ALL_LINES="0"
export TRACE_OUT="$TRACE_LOG"
export TRACE_TIME="0"
export TRACE_LIMIT="220000"
export TRACE_MAXLOCALS="200"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"

python test/qa/parse_dispatch_process_dynamic_target_oracle_v3.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" \
  --source "$SOURCE_FILE" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
