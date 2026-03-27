#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="solvers_lambert_function_call_order"
TEST_ID="tests/qa/solvers_lambert_function_call_order_test.py::TestSolversLambertFunctionCallOrderQA::test_solvers_lambert_function_call_order_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="sympy.solvers.solvers.solve,sympy.solvers.solvers._sympified_list,sympy.solvers.solvers.recast_to_symbols,sympy.solvers.solvers._solve,sympy.solvers.solvers._vsolve,sympy.solvers.solvers._tsolve,sympy.solvers.solvers._invert,sympy.solvers.solvers._ispow,sympy.solvers.solvers._as_base_q,sympy.solvers.solvers.solve_linear,sympy.solvers.solvers.unrad,sympy.solvers.solvers.denoms,sympy.solvers.solvers._simple_dens,sympy.solvers.solvers._take,sympy.solvers.solvers._has_piecewise"
export TRACE_EVENTS="call"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="80"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parse_solvers_lambert_function_call_order_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
