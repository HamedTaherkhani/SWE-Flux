#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="inputmedia_parse_file_input_call_frequency"
TEST_ID="tests/qa/inputmedia_parse_file_input_call_frequency_test.py::TestInputMediaParseFileInputCallFrequencyQA::test_inputmedia_parse_file_input_call_frequency_case"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"

TRACE_LOG="$LOG_DIR/trace.log"
PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE=""
export TRACE_FUNC="telegram._utils.files.parse_file_input,telegram._files.inputmedia.InputMediaPhoto.__init__,telegram._files.inputmedia.InputMediaVideo.__init__,telegram._files.inputmedia.InputMediaAudio.__init__,telegram._files.inputmedia.InputMediaDocument.__init__,telegram._files.inputmedia.InputMediaAnimation.__init__,telegram._files.inputmedia.InputPaidMediaPhoto.__init__,telegram._files.inputmedia.InputPaidMediaVideo.__init__,telegram._telegramobject.TelegramObject.to_dict"
export TRACE_EVENTS="call"
export TRACE_OUT="$TRACE_LOG"
export TRACE_LIMIT="300000"
export TRACE_MAXLOCALS="80"

rm -f "$TRACE_LOG" "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON"

pytest -rA -s "$TEST_ID" 2>&1 | tee "$PYTEST_LOG"
python tests/qa/parse_inputmedia_parse_file_input_call_frequency_oracle.py \
  --trace-log "$TRACE_LOG" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace log:  $TRACE_LOG"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
