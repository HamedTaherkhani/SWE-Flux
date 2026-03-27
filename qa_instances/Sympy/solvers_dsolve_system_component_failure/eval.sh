#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="solvers_dsolve_system_component_failure"
TEST_ID="tests/qa/solvers_dsolve_system_component_failure_test.py::TestSolversDsolveSystemComponentFailureQA::test_solvers_dsolve_system_component_failure_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="sympy.solvers.ode.systems._weak_component_solver"
export TRACE_EVENTS="exception"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="180"
export TRACE_FULL_LOCALS_ON_RETURN="1"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

set +e
pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
PYTEST_STATUS=${PIPESTATUS[0]}
set -e

if [[ "$PYTEST_STATUS" -eq 0 ]]; then
  echo "Expected this QA test to fail with an uncaught exception, but it passed."
  exit 1
fi

python tests/qa/parse_solvers_dsolve_system_component_failure_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
