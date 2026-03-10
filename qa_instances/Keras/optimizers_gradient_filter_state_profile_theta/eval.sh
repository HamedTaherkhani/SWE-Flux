#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="optimizers_gradient_filter_state_profile_theta"
TEST_ID="keras/src/test/optimizers/optimizers_gradient_filter_state_profile_theta_test.py::OptimizersGradientFilterStateProfileThetaQATest::test_missing_grad_paths_before_empty_grad_exception"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="keras/src/optimizers/base_optimizer.py"
export TRACE_FUNC="keras.src.optimizers.base_optimizer._filter_empty_gradients"
export TRACE_EVENTS="line,exception"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="50000"
export TRACE_MAXLOCALS="400"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python keras/src/test/parse_optimizers_gradient_filter_state_profile_theta_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
