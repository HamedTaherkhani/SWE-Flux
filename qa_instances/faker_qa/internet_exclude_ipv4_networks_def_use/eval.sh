#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
# Include the shared conftest path in PYTHONPATH
export PYTHONPATH="$ROOT_DIR:$ROOT_DIR/faker_qa/shared/files"
INSTANCE_ID="internet_exclude_ipv4_networks_def_use"
TEST_ID="faker_qa/internet_exclude_ipv4_networks_def_use/files/testcase.py::TestInternetExcludeIpv4NetworksDefUseQA::test_exclude_ipv4_networks_def_use_case"
LOG_DIR="$ROOT_DIR/logs/faker_qa/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

# Configure Tracer
export TRACE_ON="1"
export TRACE_FILE="faker/providers/internet/__init__.py"
export TRACE_FUNC="_exclude_ipv4_networks,_exclude_ipv4_network"
export TRACE_EVENTS="line,call,return,exception"
export TRACE_LOG_ALL_LINES="1"
export TRACE_OUT="$TRACE_LOG"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

# Run Test
pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"

# Run Parser
python faker_qa/internet_exclude_ipv4_networks_def_use/files/parser.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

# Sync Oracle back to instance directory
cp "$ORACLE_JSON" "$ROOT_DIR/faker_qa/internet_exclude_ipv4_networks_def_use/oracle.json"

echo "Instance:   $INSTANCE_ID"
echo "Oracle json: $ORACLE_JSON"
