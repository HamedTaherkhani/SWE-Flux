#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="regularization_dropout_repeat_profile_beta"
TEST_ID="keras/src/test/layers/regularization/dropout_repeat_profile_beta_test.py::DropoutRepeatProfileBetaQATest::test_repeated_output_profile"
REPEATS="${QA_REPEATS:-9}"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="keras/src/test/layers/regularization/dropout_repeat_profile_beta_test.py"
export TRACE_FUNC=""
export TRACE_EVENTS="return"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="50000"
export TRACE_MAXLOCALS="300"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

: > "$PYTEST_LOG"
for run_idx in $(seq 1 "$REPEATS"); do
  echo "[QA_RUN] ${run_idx}/${REPEATS}" | tee -a "$PYTEST_LOG"
  QA_RUN_INDEX="$run_idx" QA_TOTAL_RUNS="$REPEATS" \
    pytest -rA -s "$TEST_ID" 2>&1 | tee -a "$PYTEST_LOG"
done

python keras/src/test/parse_regularization_dropout_repeat_profile_beta_oracle.py \
  --pytest-log "$PYTEST_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
