#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_cursor_eval_in_docker.sh --model <model> --repo <repo|all> [options]

Options:
  --model <model>              Cursor model name (required)
  --repo <name|all>            Repo name from Repositories.json, or "all" (required)
  --num-instances <n>          Max instances per repo (default: all)
  --cursor-api-key <key>       Cursor API key (default: use CURSOR_API_KEY env var)
  --openai-api-key <key>       Optional OpenAI key input (NOT used by cursor-agent auth)
  --repos-file <path>          Path to repo->image map JSON (default: Repositories.json)
  --instances-root <path>      Host root for eval instances (default: qa_instances_eval)
  --output-root <path>         Host output root (default: evaluations/cursor)
  --container-workdir <path>   Project dir inside container (default: /testbed)
  --help                       Show help

Output layout:
  <output-root>/<model>/<repo>/<instance>/answer.json
  <output-root>/<model>/<repo>/<instance>/traj.json

Examples:
  ./run_cursor_eval_in_docker.sh --model gpt-5 --repo Sympy
  ./run_cursor_eval_in_docker.sh --model gpt-5 --repo all --num-instances 10
EOF
}

MODEL=""
REPO_ARG=""
NUM_INSTANCES="all"
CURSOR_API_KEY="${CURSOR_API_KEY:-${cursor_api_key:-${cursur_api_key:-}}}"
REPOS_FILE="Repositories.json"
INSTANCES_ROOT="qa_instances_eval"
OUTPUT_ROOT="evaluations/cursor"
CONTAINER_WORKDIR="/testbed"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="${2:-}"
      shift 2
      ;;
    --repo)
      REPO_ARG="${2:-}"
      shift 2
      ;;
    --num-instances)
      NUM_INSTANCES="${2:-}"
      shift 2
      ;;
    --cursor-api-key)
      CURSOR_API_KEY="${2:-}"
      shift 2
      ;;
    --repos-file)
      REPOS_FILE="${2:-}"
      shift 2
      ;;
    --instances-root)
      INSTANCES_ROOT="${2:-}"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="${2:-}"
      shift 2
      ;;
    --container-workdir)
      CONTAINER_WORKDIR="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$MODEL" || -z "$REPO_ARG" ]]; then
  echo "ERROR: --model and --repo are required." >&2
  usage
  exit 1
fi

if [[ ! -f "$REPOS_FILE" ]]; then
  echo "ERROR: repos file not found: $REPOS_FILE" >&2
  exit 1
fi

if [[ "$NUM_INSTANCES" != "all" ]] && ! [[ "$NUM_INSTANCES" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --num-instances must be a non-negative integer or 'all'." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required." >&2
  exit 1
fi

if ! command -v cursor-agent >/dev/null 2>&1; then
  echo "ERROR: local 'cursor-agent' is required so it can be installed into each container." >&2
  echo "Install it on host first, then rerun." >&2
  exit 1
fi

if [[ -z "$CURSOR_API_KEY" ]]; then
  echo "WARNING: CURSOR_API_KEY is not set."
  echo "Automatic login is not possible without an API key."
  echo "Set env var CURSOR_API_KEY or pass --cursor-api-key."
fi

HOST_CURSOR_AGENT_REAL="$(readlink -f "$(command -v cursor-agent)")"
HOST_CURSOR_AGENT_DIR="$(dirname "$HOST_CURSOR_AGENT_REAL")"
if [[ ! -f "$HOST_CURSOR_AGENT_DIR/index.js" || ! -x "$HOST_CURSOR_AGENT_DIR/node" ]]; then
  echo "ERROR: local cursor-agent bundle is incomplete: $HOST_CURSOR_AGENT_DIR" >&2
  exit 1
fi

MODEL_DIR_NAME="$(printf '%s' "$MODEL" | sed 's#[/[:space:]]#_#g')"
HOST_MODEL_OUT="$OUTPUT_ROOT/$MODEL_DIR_NAME"
mkdir -p "$HOST_MODEL_OUT"

mapfile -t ALL_REPOS < <(jq -r 'keys[]' "$REPOS_FILE" | sort)
if [[ ${#ALL_REPOS[@]} -eq 0 ]]; then
  echo "ERROR: no repos found in $REPOS_FILE" >&2
  exit 1
fi

TARGET_REPOS=()
if [[ "$REPO_ARG" == "all" ]]; then
  TARGET_REPOS=("${ALL_REPOS[@]}")
else
  if ! jq -e --arg r "$REPO_ARG" 'has($r)' "$REPOS_FILE" >/dev/null; then
    echo "ERROR: repo '$REPO_ARG' not found in $REPOS_FILE" >&2
    echo "Available: ${ALL_REPOS[*]}" >&2
    exit 1
  fi
  TARGET_REPOS=("$REPO_ARG")
fi

echo "Model:              $MODEL"
echo "Model output root:  $HOST_MODEL_OUT"
echo "Repos file:         $REPOS_FILE"
echo "Target repos:       ${TARGET_REPOS[*]}"
echo "Instances root:     $INSTANCES_ROOT"
echo "Container workdir:  $CONTAINER_WORKDIR"
echo "Auto auth:          $([[ -n "$CURSOR_API_KEY" ]] && echo enabled || echo disabled)"
echo

for repo in "${TARGET_REPOS[@]}"; do
  image="$(jq -r --arg r "$repo" '.[$r]' "$REPOS_FILE")"
  if [[ -z "$image" || "$image" == "null" ]]; then
    echo "[$repo] Skipping: no image configured in $REPOS_FILE"
    continue
  fi

  host_repo_instances="$INSTANCES_ROOT/$repo"
  if [[ ! -d "$host_repo_instances" ]]; then
    echo "[$repo] Skipping: missing instances dir $host_repo_instances"
    continue
  fi

  mapfile -t QUESTION_FILES < <(find "$host_repo_instances" -mindepth 2 -maxdepth 2 -type f -name question.json | sort)
  if [[ ${#QUESTION_FILES[@]} -eq 0 ]]; then
    echo "[$repo] Skipping: no question.json found"
    continue
  fi

  if [[ "$NUM_INSTANCES" == "all" ]]; then
    LIMIT=${#QUESTION_FILES[@]}
  else
    LIMIT="$NUM_INSTANCES"
    if (( LIMIT > ${#QUESTION_FILES[@]} )); then
      LIMIT=${#QUESTION_FILES[@]}
    fi
  fi

  if (( LIMIT == 0 )); then
    echo "[$repo] Skipping: --num-instances is 0"
    continue
  fi

  container_name="cursor-eval-${repo,,}-${MODEL_DIR_NAME}-$$"
  container_repo_instances="$CONTAINER_WORKDIR/qa_instances_eval/$repo"
  container_repo_out="$CONTAINER_WORKDIR/evaluations/cursor/$MODEL_DIR_NAME/$repo"
  host_repo_out="$HOST_MODEL_OUT/$repo"
  mkdir -p "$host_repo_out"

  echo "[$repo] Image: $image"
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "[$repo] Pulling missing image..."
    docker pull "$image"
  else
    echo "[$repo] Image already present."
  fi

  echo "[$repo] Starting container: $container_name"
  docker run -d --name "$container_name" -w "$CONTAINER_WORKDIR" "$image" tail -f /dev/null >/dev/null

  cleanup_repo() {
    docker rm -f "$container_name" >/dev/null 2>&1 || true
  }
  trap cleanup_repo EXIT

  docker exec "$container_name" bash -lc "mkdir -p '$CONTAINER_WORKDIR/qa_instances_eval' '$container_repo_out'"
  docker cp "$host_repo_instances" "$container_name:$CONTAINER_WORKDIR/qa_instances_eval/"

  if ! docker exec "$container_name" bash -lc "command -v cursor-agent >/dev/null 2>&1"; then
    echo "[$repo] Installing cursor-agent into container..."
    docker exec "$container_name" bash -lc "mkdir -p /opt/cursor-agent"
    docker cp "$HOST_CURSOR_AGENT_DIR/." "$container_name:/opt/cursor-agent/"
    docker exec "$container_name" bash -lc "cat >/usr/local/bin/cursor-agent <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec /opt/cursor-agent/node --use-system-ca /opt/cursor-agent/index.js \"\$@\"
EOF
chmod +x /usr/local/bin/cursor-agent"
  fi

  if ! docker exec "$container_name" bash -lc "command -v cursor-agent >/dev/null 2>&1"; then
    echo "[$repo] ERROR: failed to install cursor-agent in container."
    cleanup_repo
    trap - EXIT
    continue
  fi

  if [[ -n "$CURSOR_API_KEY" ]]; then
    echo "[$repo] Verifying cursor-agent auth (non-interactive)..."
    docker exec -e CURSOR_API_KEY="$CURSOR_API_KEY" "$container_name" bash -lc '
      set -euo pipefail
      # Keep this non-blocking. Some versions may open browser/device auth on login.
      export NO_OPEN_BROWSER=1
      if command -v timeout >/dev/null 2>&1; then
        timeout 20s cursor-agent --api-key "$CURSOR_API_KEY" whoami >/tmp/cursor-whoami.log 2>&1 || true
      else
        cursor-agent --api-key "$CURSOR_API_KEY" whoami >/tmp/cursor-whoami.log 2>&1 || true
      fi
    '
  fi

  echo "[$repo] Running $LIMIT instances..."
  for ((i = 0; i < LIMIT; i++)); do
    host_qfile="${QUESTION_FILES[$i]}"
    instance_id="$(basename "$(dirname "$host_qfile")")"
    qfile="$container_repo_instances/$instance_id/question.json"
    instance_dir="$container_repo_instances/$instance_id"
    answer_out="$container_repo_out/$instance_id/answer.json"
    run_log="$container_repo_out/$instance_id/cursor.log"
    traj_out="$container_repo_out/$instance_id/traj.json"

    echo "[$repo][$((i + 1))/$LIMIT] $instance_id"

    docker exec \
      -e MODEL="$MODEL" \
      -e QFILE="$qfile" \
      -e INSTANCE_DIR="$instance_dir" \
      -e ANSWER_OUT="$answer_out" \
      -e RUN_LOG="$run_log" \
      -e TRAJ_OUT="$traj_out" \
      -e WORKSPACE="$CONTAINER_WORKDIR" \
      -e CURSOR_API_KEY="${CURSOR_API_KEY:-}" \
      "$container_name" \
      bash -lc '
        set -euo pipefail
        mkdir -p "$(dirname "$ANSWER_OUT")"
        RAW_TRAJ_OUT="$(dirname "$ANSWER_OUT")/traj.ndjson"
        PROMPT=$(cat <<EOF
You are running a repository QA evaluation instance with full environment access.

Question file: $QFILE
Instance directory: $INSTANCE_DIR
Output file to write: $ANSWER_OUT

You have complete access to this environment: you can read/write files, run tests, and run any code/commands needed.

Required workflow:
1. Open and read "$QFILE".
2. Use BOTH the "question" field and "template_answer" field.
3. The final output must follow template_answer exactly (same top-level keys, required structure, and value types).
4. Use the instance test cases under "$INSTANCE_DIR/files/tests/qa" and referenced files to derive the answer.
5. Run tests and, if needed, add temporary logging/instrumentation to compute the correct answer.
6. Write ONLY the final JSON answer object to "$ANSWER_OUT".
7. Do not write markdown fences. Do not ask for confirmation.
8. Ensure "$ANSWER_OUT" is valid JSON before finishing.
EOF
)

        : >"$RAW_TRAJ_OUT"
        cmd_status=0
        if [[ -n "${CURSOR_API_KEY:-}" ]]; then
          cursor-agent --api-key "$CURSOR_API_KEY" -p --force --output-format stream-json --model "$MODEL" --workspace "$WORKSPACE" "$PROMPT" >"$RAW_TRAJ_OUT" 2>"$RUN_LOG" || cmd_status=$?
        else
          cursor-agent -p --force --output-format stream-json --model "$MODEL" --workspace "$WORKSPACE" "$PROMPT" >"$RAW_TRAJ_OUT" 2>"$RUN_LOG" || cmd_status=$?
        fi

        PY_BIN="$(command -v python3 || command -v python || true)"
        if [[ -n "$PY_BIN" ]]; then
          "$PY_BIN" - "$RAW_TRAJ_OUT" "$TRAJ_OUT" <<'"'"'PY'"'"'
import json
import sys

src = sys.argv[1]
dst = sys.argv[2]
events = []

with open(src, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            events.append({"type": "raw_line", "text": line})

with open(dst, "w", encoding="utf-8") as f:
    json.dump({"events": events}, f, indent=2, sort_keys=True)
    f.write("\n")
PY
        else
          cp "$RAW_TRAJ_OUT" "$TRAJ_OUT"
        fi

        if (( cmd_status != 0 )); then
          printf "cursor-agent exited with status %s\n" "$cmd_status" >>"$RUN_LOG"
        fi

        rm -f "$RAW_TRAJ_OUT"
      ' || true
  done

  docker cp "$container_name:$container_repo_out/." "$host_repo_out/"
  echo "[$repo] Copied outputs to: $host_repo_out"

  cleanup_repo
  trap - EXIT
done

echo
echo "Done. Outputs at: $HOST_MODEL_OUT"
