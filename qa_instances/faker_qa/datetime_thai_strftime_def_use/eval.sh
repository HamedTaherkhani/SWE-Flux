#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="datetime_thai_strftime_def_use"
TEST_ID="faker_qa/datetime_thai_strftime_def_use/files/testcase.py::TestDatetimeThaiStrftimeDefUseQA::test_thai_strftime_def_use_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

# Configure Tracer
export TRACE_ON="1"
export TRACE_FILE="faker/providers/date_time/th_TH/__init__.py"
export TRACE_FUNC="thai_strftime"
export TRACE_EVENTS="line,call,return,exception"
export TRACE_LOG_ALL_LINES="1"
export TRACE_OUT="$TRACE_LOG"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

# Run Test
pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"

# Run Parser
python faker_qa/datetime_thai_strftime_def_use/files/parser.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

# Sync Oracle back to instance directory
cp "$ORACLE_JSON" "$ROOT_DIR/faker_qa/datetime_thai_strftime_def_use/oracle.json"

echo "Instance:   $INSTANCE_ID"
echo "Oracle json: $ORACLE_JSON"
