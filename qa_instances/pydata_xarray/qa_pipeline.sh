#!/bin/bash
set -euo pipefail

INSTANCE_ID="${1:-}"
ROOT_DIR="${2:-/testbed}"
INSTANCES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_FILES_DIR="$INSTANCES_DIR/shared/files"
INSTANCE_DIR="$INSTANCES_DIR/$INSTANCE_ID"
INSTANCE_FILES_DIR="$INSTANCE_DIR/files"
INSTANCE_EVAL="$INSTANCE_DIR/eval.sh"

if [[ -z "$INSTANCE_ID" ]]; then
  echo "Usage: $0 <instance_id> [root_dir]"
  echo "Run this from qa_instances or call it by path."
  echo "Available instances:"
  if [[ -d "$INSTANCES_DIR" ]]; then
    find "$INSTANCES_DIR" -mindepth 1 -maxdepth 1 -type d -printf "  - %f\n" | grep -v "shared" || true
  fi
  exit 1
fi

if [[ ! -d "$INSTANCE_DIR" ]]; then
  echo "ERROR: Instance directory not found: $INSTANCE_DIR"
  exit 1
fi

cd "$ROOT_DIR"

stage_files() {
  local source_dir="$1"
  if [[ ! -d "$source_dir" ]]; then
    return 0
  fi
  while IFS= read -r -d '' src; do
    rel="${src#$source_dir/}"
    dest="$ROOT_DIR/$rel"
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
  done < <(find "$source_dir" -type f -print0)
}

# Stage shared instrumentation first, then instance-specific files.
stage_files "$SHARED_FILES_DIR"
stage_files "$INSTANCE_FILES_DIR"

if [[ ! -f "$INSTANCE_EVAL" ]]; then
  echo "ERROR: Missing instance eval script: $INSTANCE_EVAL"
  exit 1
fi

# Normalize line endings for shell execution safety in container.
perl -pi -e 's/\r//g' "$INSTANCE_EVAL"
chmod +x "$INSTANCE_EVAL"
# Invoke via bash to avoid shebang/permission edge cases on mixed host filesystems.
bash "$INSTANCE_EVAL" "$ROOT_DIR"
