#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="optimizers_step_beta1_power_coupling"
TEST_ID="keras/src/test/optimizers/optimizers_step_beta1_power_coupling_test.py::OptimizersStepBeta1PowerCouplingQATest"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="keras/src/optimizers/adam.py"
export TRACE_FUNC="keras.src.optimizers.adam.update_step"
export TRACE_EVENTS="return"
export TRACE_LOG_ALL_LINES="0"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="800"
export TRACE_MAXLOCALS="220"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python keras/src/test/parse_optimizers_step_beta1_power_coupling_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
