#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="matrices_blockmatrix_function_call_order"
TEST_ID="tests/qa/matrices_blockmatrix_function_call_order_test.py::TestMatricesBlockmatrixFunctionCallOrderQA::test_matrices_blockmatrix_function_call_order_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="sympy.matrices.expressions.blockmatrix.block_collapse,sympy.matrices.expressions.blockmatrix.bc_unpack,sympy.matrices.expressions.blockmatrix.bc_matadd,sympy.matrices.expressions.blockmatrix.bc_block_plus_ident,sympy.matrices.expressions.blockmatrix.bc_dist,sympy.matrices.expressions.blockmatrix.bc_matmul,sympy.matrices.expressions.blockmatrix.bc_transpose,sympy.matrices.expressions.blockmatrix.bc_inverse,sympy.matrices.expressions.blockmatrix.blockinverse_1x1,sympy.matrices.expressions.blockmatrix.blockinverse_2x2,sympy.matrices.expressions.blockmatrix._choose_2x2_inversion_formula,sympy.matrices.expressions.blockmatrix.deblock,sympy.matrices.expressions.blockmatrix.reblock_2x2"
export TRACE_EVENTS="call"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="80"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parse_matrices_blockmatrix_function_call_order_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
