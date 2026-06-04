#!/bin/bash
set -euo pipefail

# Host-side runner: harvest runtime metrics for one repo inside its Docker image.
#
#   ./run_repo.sh <repo_name>
#
# Resolves the image from ../../Repositories.json, starts a container, copies the
# repo's qa_instances folder + the collector scripts in, runs the collector, and
# copies analysis/runtime_metrics/raw/<repo>.json back to the host.

REPO="${1:-}"
if [[ -z "$REPO" ]]; then
  echo "Usage: $0 <repo_name>"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPOS_JSON="$PROJECT_ROOT/Repositories.json"
RAW_DIR="$SCRIPT_DIR/raw"
mkdir -p "$RAW_DIR"

IMAGE="${IMAGE:-$(python3 -c "import json,sys; print(json.load(open('$REPOS_JSON'))['$REPO'])")}"
CONTAINER_NAME="${CONTAINER_NAME:-runtime-metrics-$REPO}"
CONTAINER_REPO_DIR="/testbed"

echo "Repo:      $REPO"
echo "Image:     $IMAGE"
echo "Container: $CONTAINER_NAME"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Image not found locally. Pulling: $IMAGE"
  docker pull "$IMAGE"
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

docker run -d --name "$CONTAINER_NAME" -w "$CONTAINER_REPO_DIR" "$IMAGE" tail -f /dev/null >/dev/null

cleanup() { docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker exec "$CONTAINER_NAME" bash -lc "mkdir -p $CONTAINER_REPO_DIR/qa_instances/$REPO /opt/runtime_metrics"
docker cp "$PROJECT_ROOT/qa_instances/$REPO/." "$CONTAINER_NAME:$CONTAINER_REPO_DIR/qa_instances/$REPO/"
docker cp "$SCRIPT_DIR/metrics_plugin.py" "$CONTAINER_NAME:/opt/runtime_metrics/metrics_plugin.py"
docker cp "$SCRIPT_DIR/incontainer_collect.py" "$CONTAINER_NAME:/opt/runtime_metrics/incontainer_collect.py"

docker exec "$CONTAINER_NAME" bash -lc \
  "cd $CONTAINER_REPO_DIR && python /opt/runtime_metrics/incontainer_collect.py \
     --repo $REPO --qa-root $CONTAINER_REPO_DIR/qa_instances \
     --repo-root $CONTAINER_REPO_DIR --out /tmp/metrics_raw.json \
     --plugin-dir /opt/runtime_metrics"

docker cp "$CONTAINER_NAME:/tmp/metrics_raw.json" "$RAW_DIR/$REPO.json"
echo "Wrote raw metrics to: $RAW_DIR/$REPO.json"
