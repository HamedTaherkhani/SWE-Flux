#!/bin/bash
set -uo pipefail

# Run all QA instances from host (outside Docker), one by one.
# This script expects to live inside qa_instances/pydata_xarray.

QA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$QA_DIR/run_qa_fromhost.sh"

if [[ ! -x "$RUNNER" ]]; then
  echo "ERROR: Missing executable runner: $RUNNER"
  echo "Run: chmod +x $RUNNER"
  exit 1
fi

INSTANCES=()
while IFS= read -r d; do
  name="$(basename "$d")"
  case "$name" in
    shared|qa_artifacts)
      continue
      ;;
    *)
      INSTANCES+=("$name")
      ;;
  esac
done < <(find "$QA_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

if [[ ${#INSTANCES[@]} -eq 0 ]]; then
  echo "No QA instances found in: $QA_DIR"
  exit 1
fi

echo "Found ${#INSTANCES[@]} QA instances:"
for inst in "${INSTANCES[@]}"; do
  echo "  - $inst"
done

FAILURES=()

for inst in "${INSTANCES[@]}"; do
  echo
  echo "===== RUNNING INSTANCE: $inst ====="
  if ! HOST_QA_DIR="$QA_DIR" "$RUNNER" "$inst"; then
    FAILURES+=("$inst")
  fi
done

echo
if [[ ${#FAILURES[@]} -eq 0 ]]; then
  echo "All QA instances completed successfully."
else
  echo "Completed with ${#FAILURES[@]} failed instance(s):"
  for inst in "${FAILURES[@]}"; do
    echo "  - $inst"
  done
  exit 1
fi
echo "Artifacts root: $QA_DIR/qa_artifacts"
