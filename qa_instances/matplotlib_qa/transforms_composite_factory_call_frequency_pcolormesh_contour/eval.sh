#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="transforms_composite_factory_call_frequency_pcolormesh_contour"
TEST_ID="tests/qa/transforms_composite_factory_call_frequency_pcolormesh_contour_test.py::TestTransformsCompositeFactoryCallFrequencyPcolormeshContourQA::test_transforms_composite_factory_call_frequency_pcolormesh_contour_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export MPLBACKEND="Agg"
export TRACE_ON="1"
export TRACE_FILE="/testbed/lib/matplotlib/transforms.py"
export TRACE_FUNC="matplotlib.transforms.composite_transform_factory"
export TRACE_EVENTS="call"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="120"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parse_transforms_composite_factory_call_frequency_pcolormesh_contour_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
