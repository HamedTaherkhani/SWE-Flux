#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="faker_chained_pystruct_pydict_parse_max_call_depth"
TEST_ID="testcase.py::TestFakerChainedPystructPydictParseMaxCallDepthQA::test_faker_chained_pystruct_pydict_parse_max_call_depth_case"
LOG_DIR="$ROOT_DIR/logs/faker_qa/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="faker/"
export TRACE_FUNC=""
export TRACE_EVENTS="call,return"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="8000000"
export TRACE_MAXLOCALS="25"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python parser.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

cp "$ORACLE_JSON" "$ROOT_DIR/faker_qa/$INSTANCE_ID/oracle.json"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
