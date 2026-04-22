#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="core_manager_restart_state_init_execution_path_lines"
TEST_ID="tests/qa/core_manager_restart_state_init_execution_path_lines_test.py::TestCoreManagerRestartStateInitExecutionPathLinesQA::test_core_manager_restart_state_init_execution_path_lines_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="libqtile.core.manager.restart,libqtile.core.manager.Qtile.restart,libqtile.core.manager.dump_state,libqtile.core.manager.Qtile.dump_state,libqtile.core.manager._stop,libqtile.core.manager.Qtile._stop,libqtile.core.state.__init__,libqtile.core.state.QtileState.__init__"
export TRACE_EVENTS="line"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="80"
export TRACE_LOG_ALL_LINES="1"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parse_core_manager_restart_state_init_execution_path_lines_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
