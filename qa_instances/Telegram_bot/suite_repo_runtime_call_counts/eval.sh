#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="suite_repo_runtime_call_counts"
INSTANCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QA_ROOT_DIR="$(cd "$INSTANCE_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs/qa_instances/$INSTANCE_ID"
TRACE_DIR="$LOG_DIR/traces"
MANIFEST_FILE="$LOG_DIR/test_manifest.tsv"
TESTS_DIR="$ROOT_DIR/tests/qa"

PYTEST_LOG="$LOG_DIR/pytest.log"
ORACLE_LOG="$LOG_DIR/oracle.log"
ORACLE_JSON="$LOG_DIR/oracle.json"

mkdir -p "$LOG_DIR" "$TRACE_DIR"
cd "$ROOT_DIR"

export TRACE_ON="1"
export TRACE_FILE="/testbed/telegram/"
export TRACE_FUNC=""
export TRACE_EVENTS="call"
export TRACE_LIMIT="50000"
export TRACE_MAXLOCALS="200"
export TRACE_FULL_LOCALS_ON_RETURN="0"

rm -f "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON" "$MANIFEST_FILE"
rm -f "$TRACE_DIR"/*.log 2>/dev/null || true

mkdir -p "$TESTS_DIR"
find "$TESTS_DIR" -maxdepth 1 -type f -name "*_test.py" -delete
while IFS= read -r src; do
  cp "$src" "$TESTS_DIR/$(basename "$src")"
done < <(find "$QA_ROOT_DIR" -type f -path "*/files/tests/qa/*_test.py" | sort)

mapfile -t TEST_FILES < <(find "$TESTS_DIR" -maxdepth 1 -type f -name "*_test.py" | sort)
if [[ ${#TEST_FILES[@]} -eq 0 ]]; then
  echo "ERROR: No test files found after staging into $TESTS_DIR"
  exit 1
fi

mapfile -t TEST_IDS < <(pytest "${TEST_FILES[@]}" --collect-only -q | grep "::" | sort)

if [[ ${#TEST_IDS[@]} -eq 0 ]]; then
  echo "ERROR: No tests collected from tests/qa/*_test.py"
  exit 1
fi

for idx in "${!TEST_IDS[@]}"; do
  test_id="${TEST_IDS[$idx]}"
  trace_log="$TRACE_DIR/$(printf '%03d' "$idx").log"
  export TRACE_OUT="$trace_log"
  echo -e "${test_id}\t${trace_log}" >>"$MANIFEST_FILE"
  echo "===== RUNNING TEST: $test_id =====" | tee -a "$PYTEST_LOG"
  pytest -rA -s "$test_id" 2>&1 | tee -a "$PYTEST_LOG"
done

python tests/qa/parse_suite_repo_runtime_call_counts_oracle.py \
  --manifest "$MANIFEST_FILE" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace dir:  $TRACE_DIR"
echo "Manifest:   $MANIFEST_FILE"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
