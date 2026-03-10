#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="layers_rescaling_block_reachability_easy"
TEST_ID="keras/src/test/layers/preprocessing/rescaling_block_reachability_easy_test.py::RescalingBlockReachabilityEasyQATest::test_channels_first_scale_reshape_block_reachability"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="keras/src/layers/preprocessing/rescaling.py"
export TRACE_FUNC="keras.src.layers.preprocessing.rescaling.call"
export TRACE_EVENTS="line"
export TRACE_LOG_ALL_LINES="1"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200"
export TRACE_MAXLOCALS="120"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python keras/src/test/parse_layers_rescaling_block_reachability_easy_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
