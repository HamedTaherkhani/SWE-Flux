#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="sam_replace_local_codeuri_state"
TEST_ID="tests/qa/testcase.py::TestSamReplaceLocalCodeuriStateQA::test_sam_replace_local_codeuri_state_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="cfnlint/template/transforms/_sam.py"
export TRACE_FUNC="cfnlint.template.transforms._sam.Transform._replace_local_codeuri"
export TRACE_EVENTS="return"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="500000"
export TRACE_MAXLOCALS="120"
export TRACE_FULL_LOCALS_ON_RETURN="1"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parser.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
