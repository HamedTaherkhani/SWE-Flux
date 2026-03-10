#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="tree_recursive_trace_profile_delta"
TEST_ID="keras/src/test/tree/tree_recursive_trace_profile_delta_test.py::TreeRecursiveTraceProfileDeltaQATest::test_single_recursive_walk_signature"
REPEATS="${QA_REPEATS:-11}"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="keras/src/tree/dmtree_impl.py"
export TRACE_FUNC="keras.src.tree.dmtree_impl._recursive_flatten_with_path"
export TRACE_EVENTS="call,line,return"
export TRACE_LOG_ALL_LINES="1"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="1000"
export TRACE_MAXLOCALS="200"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

: > "$PYTEST_LOG"
for run_idx in $(seq 1 "$REPEATS"); do
  echo "[QA_RUN] ${run_idx}/${REPEATS}" | tee -a "$PYTEST_LOG"
  pytest -rA -s "$TEST_ID" 2>&1 | tee -a "$PYTEST_LOG"
done

python keras/src/test/parse_tree_recursive_trace_profile_delta_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
