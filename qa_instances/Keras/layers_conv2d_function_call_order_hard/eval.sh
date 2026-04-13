#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="layers_conv2d_function_call_order_hard"
TEST_ID="keras/src/test/layers/convolutional/conv2d_function_call_order_hard_test.py::Conv2DFunctionCallOrderHardQATest::test_conv2d_function_call_order_grouped_channels_first_bias_activation"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="keras.src.layers.convolutional.conv2d,keras.src.layers.convolutional.base_conv,keras.src.activations.activations,keras.src.backend.tensorflow.nn.relu,keras.src.backend.tensorflow.nn.conv,keras.src.backend.tensorflow.nn._conv,keras.src.backend.tensorflow.nn._convert_data_format"
export TRACE_EVENTS="call"
export TRACE_LOG_ALL_LINES="0"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200"
export TRACE_MAXLOCALS="120"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python keras/src/test/parse_layers_conv2d_function_call_order_hard_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
