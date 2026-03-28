#!/bin/bash
set -euo pipefail

INSTANCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$INSTANCE_DIR/run_qa_fromhost.sh"
MERGER="$INSTANCE_DIR/merge_repo_oracles.py"
HOST_OUTPUT_DIR="${HOST_OUTPUT_DIR:-$INSTANCE_DIR/qa_artifacts}"
MERGED_OUT="${MERGED_OUT:-$HOST_OUTPUT_DIR/oracle.merged.json}"

if [[ ! -x "$RUNNER" ]]; then
  echo "ERROR: Missing executable runner: $RUNNER"
  echo "Run: chmod +x $RUNNER"
  exit 1
fi
if [[ ! -f "$MERGER" ]]; then
  echo "ERROR: Missing merger script: $MERGER"
  exit 1
fi

REPOS=("$@")
if [[ ${#REPOS[@]} -eq 0 ]]; then
  REPOS=("Keras" "Telegram_bot", "Sympy")
fi

INPUTS=()
for repo in "${REPOS[@]}"; do
  echo
  echo "===== RUNNING REPO: $repo ====="
  HOST_OUTPUT_DIR="$HOST_OUTPUT_DIR" "$RUNNER" "$repo"
  INPUTS+=("$HOST_OUTPUT_DIR/$repo/oracle.json")
done

echo
echo "===== MERGING RESULTS ====="
python "$MERGER" --out "$MERGED_OUT" --inputs "${INPUTS[@]}"

echo
echo "Done."
echo "Merged oracle: $MERGED_OUT"
