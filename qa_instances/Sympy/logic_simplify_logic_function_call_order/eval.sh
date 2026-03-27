#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="logic_simplify_logic_function_call_order"
TEST_ID="tests/qa/logic_simplify_logic_function_call_order_test.py::TestLogicSimplifyLogicFunctionCallOrderQA::test_logic_simplify_logic_function_call_order_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="sympy.logic.boolalg.simplify_logic,sympy.logic.boolalg._find_predicates,sympy.logic.boolalg._get_truthtable,sympy.logic.boolalg._finger,sympy.logic.boolalg.SOPform,sympy.logic.boolalg._sop_form,sympy.logic.boolalg._input_to_binlist,sympy.logic.boolalg._simplified_pairs,sympy.logic.boolalg._check_pair,sympy.logic.boolalg._rem_redundancy,sympy.logic.boolalg._convert_to_varsSOP"
export TRACE_EVENTS="call"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="80"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parse_logic_simplify_logic_function_call_order_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
