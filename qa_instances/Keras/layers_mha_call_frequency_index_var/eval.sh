#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="layers_mha_call_frequency_index_var"
TEST_ID="keras/src/test/layers/attention/mha_call_frequency_index_var_test.py::MultiHeadAttentionCallFrequencyIndexVarQATest::test_index_to_einsum_variable_call_frequency"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="keras.src.layers.attention.multi_head_attention"
export TRACE_EVENTS="call"
export TRACE_LOG_ALL_LINES="0"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200"
export TRACE_MAXLOCALS="120"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python keras/src/test/parse_layers_mha_call_frequency_index_var_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
