#!/bin/bash
set -euo pipefail

ROOT_DIR="${1:-/testbed}"
INSTANCE_ID="suite_repo_runtime_call_counts"
INSTANCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QA_ROOT_DIR="$(cd "$INSTANCE_DIR/.." && pwd)"
LOG_DIR="$INSTANCE_DIR"
TRACE_DIR="$INSTANCE_DIR/traces"
MANIFEST_FILE="$INSTANCE_DIR/test_manifest.tsv"

PYTEST_LOG="$INSTANCE_DIR/pytest.log"
ORACLE_LOG="$INSTANCE_DIR/oracle.log"
ORACLE_JSON="$INSTANCE_DIR/oracle.json"

mkdir -p "$LOG_DIR" "$TRACE_DIR"

if [[ ! -d "$ROOT_DIR" ]]; then
  echo "ERROR: ROOT_DIR does not exist: $ROOT_DIR"
  exit 1
fi

export TRACE_ON="1"
export TRACE_FILE="$ROOT_DIR/telegram/"
export TRACE_FUNC=""
export TRACE_EVENTS="call"
export TRACE_LIMIT="50000"
export TRACE_MAXLOCALS="200"
export TRACE_FULL_LOCALS_ON_RETURN="0"
export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"
TARGET_REPOS="${TARGET_REPOS:-}"

rm -f "$PYTEST_LOG" "$ORACLE_LOG" "$ORACLE_JSON" "$MANIFEST_FILE"
rm -f "$TRACE_DIR"/*.log 2>/dev/null || true

trace_prefix_for_repo() {
  local repo_name="$1"
  local repo_lower
  repo_lower="$(echo "$repo_name" | tr '[:upper:]' '[:lower:]')"
  if [[ "$repo_lower" == *telegram* ]]; then
    echo "$ROOT_DIR/telegram/"
  elif [[ "$repo_lower" == *keras* ]]; then
    echo "$ROOT_DIR/keras/src/"
  else
    echo "$ROOT_DIR/${repo_lower}/"
  fi
}

collect_test_ids() {
  python - "$@" <<'PY'
import sys
import pytest

test_files = sys.argv[1:]


class NodeIdCollector:
    def pytest_collection_finish(self, session):
        for item in session.items:
            print(item.nodeid)


args = test_files + ["--collect-only", "-q"]
rc = pytest.main(args, plugins=[NodeIdCollector()])
sys.exit(0 if rc in (0, 5) else rc)
PY
}

mapfile -t REPO_DIRS < <(
  find "$QA_ROOT_DIR" -mindepth 1 -maxdepth 1 -type d \
    ! -name "shared" ! -name "qa_artifacts" ! -name "$INSTANCE_ID" | sort
)

if [[ -n "$TARGET_REPOS" ]]; then
  FILTERED_REPO_DIRS=()
  for repo_dir in "${REPO_DIRS[@]}"; do
    repo_name="$(basename "$repo_dir")"
    for wanted in ${TARGET_REPOS//,/ }; do
      if [[ "$repo_name" == "$wanted" ]]; then
        FILTERED_REPO_DIRS+=("$repo_dir")
        break
      fi
    done
  done
  REPO_DIRS=("${FILTERED_REPO_DIRS[@]}")
fi

if [[ ${#REPO_DIRS[@]} -eq 0 ]]; then
  echo "ERROR: No repository directories found under $QA_ROOT_DIR (TARGET_REPOS='${TARGET_REPOS}')"
  exit 1
fi

trace_idx=0

for repo_dir in "${REPO_DIRS[@]}"; do
  repo_name="$(basename "$repo_dir")"
  repo_trace_prefix="$(trace_prefix_for_repo "$repo_name")"

  echo "===== DISCOVERING REPO: $repo_name (TRACE_FILE=$repo_trace_prefix) =====" | tee -a "$PYTEST_LOG"

  # Stage shared support files (e.g. conftest.py / trace plugins) into the container repo.
  if [[ -d "$repo_dir/shared/files" ]]; then
    while IFS= read -r shared_src; do
      rel_path="${shared_src#"$repo_dir/shared/files/"}"
      dst_path="$ROOT_DIR/$rel_path"
      mkdir -p "$(dirname "$dst_path")"
      cp "$shared_src" "$dst_path"
    done < <(find "$repo_dir/shared/files" -type f | sort)
  fi

  mapfile -t SRC_TEST_FILES < <(
    find "$repo_dir" -type f -path "*/files/*_test.py" \
      ! -path "*/shared/*" ! -path "*/qa_artifacts/*" | sort
  )
  if [[ ${#SRC_TEST_FILES[@]} -eq 0 ]]; then
    echo "WARNING: No QA test files found for repo $repo_name; skipping." | tee -a "$PYTEST_LOG"
    continue
  fi

  DEST_TEST_FILES=()
  FILE_INSTANCE_MAP="$TRACE_DIR/${repo_name}_file_instance_map.tsv"
  : >"$FILE_INSTANCE_MAP"
  for src_test in "${SRC_TEST_FILES[@]}"; do
    instance_rel="${src_test#"$repo_dir/"}"
    instance_name="${instance_rel%%/*}"
    rel_path="${src_test#*"/files/"}"
    dst_path="$ROOT_DIR/$rel_path"
    mkdir -p "$(dirname "$dst_path")"
    cp "$src_test" "$dst_path"
    DEST_TEST_FILES+=("$dst_path")
    echo -e "${rel_path}\t${instance_name}" >>"$FILE_INSTANCE_MAP"
  done

  collect_log="$TRACE_DIR/${repo_name}_collect.log"
  if ! collect_test_ids "${DEST_TEST_FILES[@]}" >"$collect_log" 2>>"$PYTEST_LOG"; then
    echo "WARNING: Test collection failed for repo $repo_name; see $PYTEST_LOG." | tee -a "$PYTEST_LOG"
    continue
  fi

  mapfile -t TEST_IDS < <(grep "::" "$collect_log" | sort)
  if [[ ${#TEST_IDS[@]} -eq 0 ]]; then
    echo "WARNING: No tests collected for repo $repo_name; skipping. Collector output: $collect_log" | tee -a "$PYTEST_LOG"
    continue
  fi

  for test_id in "${TEST_IDS[@]}"; do
    test_file="${test_id%%::*}"
    instance_name="$(awk -F $'\t' -v f="$test_file" '$1==f{print $2; exit}' "$FILE_INSTANCE_MAP")"
    if [[ -z "$instance_name" ]]; then
      instance_name="unknown_instance"
    fi

    trace_log="$TRACE_DIR/${repo_name}_$(printf '%04d' "$trace_idx").log"
    export TRACE_FILE="$repo_trace_prefix"
    export TRACE_OUT="$trace_log"

    echo -e "${repo_name}\t${instance_name}\t${test_id}\t${trace_log}\t${repo_trace_prefix}" >>"$MANIFEST_FILE"
    echo "===== RUNNING [$repo_name] TEST: $test_id =====" | tee -a "$PYTEST_LOG"
    pytest -rA -s "$test_id" 2>&1 | tee -a "$PYTEST_LOG"
    trace_idx=$((trace_idx + 1))
  done
done

if [[ ! -s "$MANIFEST_FILE" ]]; then
  echo "ERROR: Manifest is empty. No tests were run."
  exit 1
fi

python "$INSTANCE_DIR/files/tests/qa/parse_suite_repo_runtime_call_counts_oracle.py" \
  --manifest "$MANIFEST_FILE" \
  --out "$ORACLE_JSON" | tee "$ORACLE_LOG"

echo "Instance:   $INSTANCE_ID"
echo "Pytest log: $PYTEST_LOG"
echo "Trace dir:  $TRACE_DIR"
echo "Manifest:   $MANIFEST_FILE"
echo "Oracle log: $ORACLE_LOG"
echo "Oracle json:$ORACLE_JSON"
