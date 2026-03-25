#!/bin/bash
set -euo pipefail

TARGET_REPO="${1:-}"

INSTANCE_ID="suite_repo_runtime_call_counts"
INSTANCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST_QA_ROOT="$(cd "$INSTANCE_DIR/.." && pwd)"
HOST_OUTPUT_DIR="${HOST_OUTPUT_DIR:-$INSTANCE_DIR/qa_artifacts}"

CONTAINER_REPO_DIR="/testbed"
CONTAINER_QA_DIR="$CONTAINER_REPO_DIR/qa_instances"
CONTAINER_INSTANCE_DIR="$CONTAINER_QA_DIR/$INSTANCE_ID"

if [[ -z "$TARGET_REPO" ]]; then
  echo "Usage: $0 <repo_name>"
  echo "Example: $0 Keras"
  echo "Example: $0 Telegram_bot"
  exit 1
fi

case "$TARGET_REPO" in
  Keras)
    DEFAULT_IMAGE="starryzhang/sweb.eval.x86_64.keras-team_1776_keras-21072:latest"
    ;;
  Telegram_bot)
    DEFAULT_IMAGE="starryzhang/sweb.eval.x86_64.python-telegram-bot_1776_python-telegram-bot-4673:latest"
    ;;
  *)
    echo "ERROR: Unsupported repo '$TARGET_REPO'. Supported: Keras, Telegram_bot"
    exit 1
    ;;
esac

IMAGE="${IMAGE:-$DEFAULT_IMAGE}"
CONTAINER_NAME="${CONTAINER_NAME:-qa-suite-runtime-${TARGET_REPO,,}}"

echo "Repo:           $TARGET_REPO"
echo "Image:          $IMAGE"
echo "Container name: $CONTAINER_NAME"
echo "Host qa root:   $HOST_QA_ROOT"
echo "Host output dir:$HOST_OUTPUT_DIR"

if [[ ! -d "$HOST_QA_ROOT/$TARGET_REPO" ]]; then
  echo "ERROR: Missing repo QA directory: $HOST_QA_ROOT/$TARGET_REPO"
  exit 1
fi
if [[ ! -d "$INSTANCE_DIR" ]]; then
  echo "ERROR: Missing instance directory: $INSTANCE_DIR"
  exit 1
fi

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Image not found locally. Pulling: $IMAGE"
  docker pull "$IMAGE"
else
  echo "Image already available locally."
fi

cleanup() {
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

docker run -d \
  --name "$CONTAINER_NAME" \
  -w "$CONTAINER_REPO_DIR" \
  "$IMAGE" \
  tail -f /dev/null >/dev/null

docker exec "$CONTAINER_NAME" bash -lc "mkdir -p $CONTAINER_QA_DIR"
docker cp "$HOST_QA_ROOT/." "$CONTAINER_NAME:$CONTAINER_QA_DIR"

set +e
docker exec \
  -e TARGET_REPOS="$TARGET_REPO" \
  "$CONTAINER_NAME" \
  bash -lc "chmod +x $CONTAINER_INSTANCE_DIR/eval.sh && $CONTAINER_INSTANCE_DIR/eval.sh $CONTAINER_REPO_DIR"
RUN_STATUS=$?
set -e

REPO_OUTPUT_DIR="$HOST_OUTPUT_DIR/$TARGET_REPO"
mkdir -p "$REPO_OUTPUT_DIR"

for file_name in oracle.json oracle.log pytest.log test_manifest.tsv; do
  if docker exec "$CONTAINER_NAME" bash -lc "test -f $CONTAINER_INSTANCE_DIR/$file_name"; then
    docker cp "$CONTAINER_NAME:$CONTAINER_INSTANCE_DIR/$file_name" "$REPO_OUTPUT_DIR/$file_name"
  fi
done

if docker exec "$CONTAINER_NAME" bash -lc "test -d $CONTAINER_INSTANCE_DIR/traces"; then
  rm -rf "$REPO_OUTPUT_DIR/traces"
  mkdir -p "$REPO_OUTPUT_DIR/traces"
  docker cp "$CONTAINER_NAME:$CONTAINER_INSTANCE_DIR/traces/." "$REPO_OUTPUT_DIR/traces/"
fi

echo "Completed: $TARGET_REPO"
echo "Artifacts: $REPO_OUTPUT_DIR"

if [[ $RUN_STATUS -ne 0 ]]; then
  echo "ERROR: suite run failed in container (exit=$RUN_STATUS)."
  echo "Check logs in: $REPO_OUTPUT_DIR"
  exit $RUN_STATUS
fi
