#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="linux_desktop_environment_execution_path"
TEST_ID="test/qa/linux_desktop_environment_execution_path_test.py::TestLinuxDesktopEnvironmentExecutionPathQA::test_linux_desktop_environment_execution_path_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="yt_dlp.cookies._get_linux_desktop_environment"
export TRACE_EVENTS="line"
export TRACE_LOG_ALL_LINES="1"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="400"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python test/qa/parse_linux_desktop_environment_execution_path_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
