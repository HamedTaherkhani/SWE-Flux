#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="components_foreach_render_execution_path_lines"
TEST_ID="tests/qa/components_foreach_render_execution_path_lines_test.py::TestComponentsForeachRenderExecutionPathLinesQA::test_components_foreach_render_execution_path_lines_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="/testbed/reflex/components"
export TRACE_FUNC="reflex.components.core.foreach.Foreach.create,reflex.components.core.foreach.Foreach._render,reflex.components.core.foreach.Foreach.render,reflex.components.tags.iter_tag.IterTag.render_component,reflex.components.tags.iter_tag.IterTag.get_arg_var,reflex.components.tags.iter_tag.IterTag.get_index_var,reflex.components.tags.iter_tag.IterTag.get_arg_var_arg,reflex.components.tags.iter_tag.IterTag.get_index_var_arg,reflex.components.tags.iter_tag.IterTag.get_iterable_var_type,reflex.components.component.Component.create,reflex.components.component.Component._create"
export TRACE_EVENTS="line"
export TRACE_LOG_ALL_LINES="1"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="80"
export TRACE_FULL_LOCALS_ON_RETURN="1"
export TRACE_NO_UNDERSCORE="0"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

PYTEST_BIN="${PYTEST_BIN:-$ROOT_DIR/.venv/bin/pytest}"
if [[ ! -x "$PYTEST_BIN" ]]; then
  PYTEST_BIN="pytest"
fi

"$PYTEST_BIN" -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parse_components_foreach_render_execution_path_lines_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
