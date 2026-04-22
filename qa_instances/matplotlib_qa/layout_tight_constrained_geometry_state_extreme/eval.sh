#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="layout_tight_constrained_geometry_state_extreme"
TEST_ID="tests/qa/layout_tight_constrained_geometry_state_extreme_test.py::TestLayoutTightConstrainedGeometryStateExtremeQA::test_layout_tight_constrained_geometry_state_extreme_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="matplotlib.figure.Figure.get_tightbbox,matplotlib._tight_layout.get_tight_layout_figure"
export TRACE_EVENTS="return,line"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="800000"
export TRACE_MAXLOCALS="200"
export TRACE_FULL_LOCALS_ON_RETURN="1"
export TRACE_LOG_ALL_LINES="1"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parse_layout_tight_constrained_geometry_state_extreme_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
