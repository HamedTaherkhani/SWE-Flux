#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="misc_provider_password_line_path_determinism"
TEST_ID="testcase.py::TestMiscProviderPasswordLinePathDeterminismQA::test_misc_provider_password_line_path_determinism_case"
LOG_DIR="$ROOT_DIR/logs/faker_qa/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="faker/providers/misc"
# CPython 3.10 traces as module+co_name; 3.11+ may include class in co_qualname.
export TRACE_FUNC="faker.providers.misc.password,faker.providers.misc.Provider.password"
export TRACE_EVENTS="line,call,return,exception"
export TRACE_LOG_ALL_LINES="1"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="1200"
export TRACE_MAXLOCALS="150"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

for run in $(seq 1 10); do
  echo "=== RUN $run/10 ===" | tee -a "$PYTEST_LOG"
  pytest -rA -s "$TEST_ID" 2>&1 | tee -a "$PYTEST_LOG"
done

python parser.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

cp "$ORACLE_JSON" "$ROOT_DIR/faker_qa/$INSTANCE_ID/oracle.json"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
