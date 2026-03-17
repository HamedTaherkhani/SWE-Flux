#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="applicationbuilder_request_block_reachability"
TEST_ID="tests/qa/applicationbuilder_request_block_reachability_test.py::TestApplicationBuilderRequestBlockReachabilityQA::test_applicationbuilder_request_block_reachability_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="telegram.ext._applicationbuilder.ApplicationBuilder.build,telegram.ext._applicationbuilder.ApplicationBuilder._build_ext_bot,telegram.ext._applicationbuilder.ApplicationBuilder._build_request,telegram.request._httpxrequest.HTTPXRequest.__init__,telegram.ext._extbot.ExtBot.__init__,telegram.ext._updater.Updater.__init__,telegram.ext._application.Application.__init__"
export TRACE_EVENTS="line,call,return"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="120"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parse_applicationbuilder_request_block_reachability_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
