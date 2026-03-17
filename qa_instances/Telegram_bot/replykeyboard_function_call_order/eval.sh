#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="replykeyboard_function_call_order"
TEST_ID="tests/qa/replykeyboard_function_call_order_test.py::TestReplyKeyboardFunctionCallOrderQA::test_replykeyboard_function_call_order_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="telegram._webappinfo.WebAppInfo.__init__,telegram._keyboardbutton.KeyboardButton.__init__,telegram._replykeyboardmarkup.ReplyKeyboardMarkup.__init__,telegram._utils.markup.check_keyboard_type,telegram._telegramobject.TelegramObject.to_dict,telegram._telegramobject.TelegramObject._get_attrs,telegram._telegramobject.TelegramObject._get_attrs_names"
export TRACE_EVENTS="call"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="200000"
export TRACE_MAXLOCALS="40"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parse_replykeyboard_function_call_order_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
