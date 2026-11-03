#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  evaluation_scripts/run_cursor_eval_in_docker.sh --model <model> --repo <repo|all> [options]

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
  --resume                     Skip instances that already have non-empty answer.json
  --no-exec                    Static mode: the agent gets a READ-ONLY copy of the repo and
                               cannot run any shell command (no tests, no python). Runs inside
                               a minimal sandbox image instead of the repo's environment image.
                               Default output root becomes evaluations/cursor-noexec.
  --sandbox-image <image>      Base image for --no-exec sandbox (default: ubuntu:22.04).
                               Must NOT contain python or the project environment.
  --help                       Show help

Output layout:
  <output-root>/<model>/<repo>/<instance>/answer.json
  <output-root>/<model>/<repo>/<instance>/traj.json

Examples:
  ./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5 --repo Sympy
  ./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5 --repo Sympy --no-exec
  ./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5 --repo all --num-instances 10
EOF
}

MODEL=""
REPO_ARG=""
NUM_INSTANCES="all"
CURSOR_API_KEY="${CURSOR_API_KEY:-${cursor_api_key:-${cursur_api_key:-}}}"
REPOS_FILE="$REPO_ROOT/Repositories.json"
INSTANCES_ROOT="$REPO_ROOT/qa_instances_eval"
OUTPUT_ROOT=""
CONTAINER_WORKDIR="/testbed"
RESUME="0"
NO_EXEC="0"
SANDBOX_IMAGE="ubuntu:22.04"

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
    --resume)
      RESUME="1"
      shift
      ;;
    --no-exec)
      NO_EXEC="1"
      shift
      ;;
    --sandbox-image)
      SANDBOX_IMAGE="${2:-}"
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

if [[ -z "$OUTPUT_ROOT" ]]; then
  if [[ "$NO_EXEC" == "1" ]]; then
    OUTPUT_ROOT="$REPO_ROOT/evaluations/cursor-noexec"
  else
    OUTPUT_ROOT="$REPO_ROOT/evaluations/cursor"
  fi
fi
# Tool directory name under <workdir>/evaluations/ inside the container mirrors the host layout.
TOOL_DIR_NAME="$(basename "$OUTPUT_ROOT")"

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
echo "Resume mode:        $([[ "$RESUME" == "1" ]] && echo enabled || echo disabled)"
echo "Auto auth:          $([[ -n "$CURSOR_API_KEY" ]] && echo enabled || echo disabled)"
echo "Execution:          $([[ "$NO_EXEC" == "1" ]] && echo "DISABLED (static, sandbox image: $SANDBOX_IMAGE)" || echo "enabled (full env access)")"
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
  container_repo_out="$CONTAINER_WORKDIR/evaluations/$TOOL_DIR_NAME/$MODEL_DIR_NAME/$repo"
  host_repo_out="$HOST_MODEL_OUT/$repo"
  mkdir -p "$host_repo_out"

  if [[ "$RESUME" == "1" ]]; then
    pending=0
    for ((i = 0; i < LIMIT; i++)); do
      host_qfile="${QUESTION_FILES[$i]}"
      instance_id="$(basename "$(dirname "$host_qfile")")"
      host_answer="$host_repo_out/$instance_id/answer.json"
      if [[ ! -s "$host_answer" ]]; then
        pending=$((pending + 1))
      fi
    done
    if (( pending == 0 )); then
      echo "[$repo] Skipping: all $LIMIT selected instances already have answer.json"
      continue
    fi
    echo "[$repo] Resume: $pending/$LIMIT instances pending"
  fi

  echo "[$repo] Image: $image"
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "[$repo] Pulling missing image..."
    docker pull "$image"
  else
    echo "[$repo] Image already present."
  fi

  echo "[$repo] Starting container: $container_name"
  docker run -d --name "$container_name" -w "$CONTAINER_WORKDIR" "$image" tail -f /dev/null >/dev/null

  env_container_name="$container_name"
  sandbox_container_name="${container_name}-sandbox"
  snapshot_dir=""

  cleanup_repo() {
    docker rm -f "$env_container_name" >/dev/null 2>&1 || true
    docker rm -f "$sandbox_container_name" >/dev/null 2>&1 || true
    if [[ -n "$snapshot_dir" && -d "$snapshot_dir" ]]; then
      rm -rf "$snapshot_dir" || true
    fi
  }
  trap cleanup_repo EXIT

  docker exec "$container_name" bash -lc "mkdir -p '$CONTAINER_WORKDIR/qa_instances_eval' '$container_repo_out'"
  docker cp "$host_repo_instances" "$container_name:$CONTAINER_WORKDIR/qa_instances_eval/"

  if [[ "$NO_EXEC" == "1" ]]; then
    # Static mode: snapshot the repo (plus instances) out of the environment image, drop the
    # environment container, and run the agent in a minimal sandbox where the repo is mounted
    # read-only and no interpreter/test environment exists. Only the output dir is writable.
    snapshot_dir="$(mktemp -d "${TMPDIR:-/tmp}/cursor-noexec-${repo,,}-XXXXXX")"
    echo "[$repo] Snapshotting $CONTAINER_WORKDIR from environment image -> $snapshot_dir"
    docker cp "$env_container_name:$CONTAINER_WORKDIR/." "$snapshot_dir/"
    docker rm -f "$env_container_name" >/dev/null 2>&1 || true
    mkdir -p "$snapshot_dir/evaluations/$TOOL_DIR_NAME/$MODEL_DIR_NAME/$repo"

    if ! docker image inspect "$SANDBOX_IMAGE" >/dev/null 2>&1; then
      echo "[$repo] Pulling sandbox image $SANDBOX_IMAGE..."
      docker pull "$SANDBOX_IMAGE"
    fi

    echo "[$repo] Starting sandbox container: $sandbox_container_name"
    docker run -d --name "$sandbox_container_name" -w "$CONTAINER_WORKDIR" \
      -v "$snapshot_dir:$CONTAINER_WORKDIR:ro" \
      -v "$host_repo_out:$container_repo_out" \
      -v /etc/ssl/certs:/etc/ssl/certs:ro \
      -e SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
      -e HOME=/root \
      "$SANDBOX_IMAGE" tail -f /dev/null >/dev/null
    container_name="$sandbox_container_name"

    # Hard guard: the sandbox image must not expose the project environment.
    if docker exec "$container_name" bash -lc "command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || command -v pytest >/dev/null 2>&1"; then
      echo "[$repo] ERROR: sandbox image '$SANDBOX_IMAGE' contains python/pytest; refusing to run --no-exec." >&2
      cleanup_repo
      trap - EXIT
      continue
    fi
  fi

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

  if [[ "$NO_EXEC" == "1" ]]; then
    # Soft guard: deny every shell command at the Cursor permission layer. --force honours
    # explicit deny rules, so the agent's Shell tool is rejected before anything is spawned.
    docker exec "$container_name" bash -lc "mkdir -p \$HOME/.cursor && cat >\$HOME/.cursor/cli-config.json <<'EOF'
{
  \"version\": 1,
  \"permissions\": {
    \"allow\": [],
    \"deny\": [\"Shell(*)\"]
  },
  \"approvalMode\": \"allowlist\",
  \"sandbox\": { \"mode\": \"disabled\" }
}
EOF"
    echo "[$repo] Cursor permissions: Shell(*) denied; repo mounted read-only."
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
    host_instance_out="$host_repo_out/$instance_id"
    host_answer="$host_instance_out/answer.json"

    if [[ "$RESUME" == "1" && -s "$host_answer" ]]; then
      echo "[$repo][$((i + 1))/$LIMIT] $instance_id (skip: answer exists)"
      continue
    fi

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
      -e NO_EXEC="$NO_EXEC" \
      "$container_name" \
      bash -lc '
        set -euo pipefail
        mkdir -p "$(dirname "$ANSWER_OUT")"
        RAW_TRAJ_OUT="$(dirname "$ANSWER_OUT")/traj.ndjson"
        if [[ "$NO_EXEC" == "1" ]]; then
        PROMPT=$(cat <<EOF
You are running a repository QA evaluation instance in STATIC mode (no code execution).

Question file: $QFILE
Instance directory: $INSTANCE_DIR
Output file to write: $ANSWER_OUT

Constraints of this environment:
- The repository is mounted READ-ONLY and there is NO Python interpreter or test runner available.
- You CANNOT run shell commands, tests, or any code; such tool calls are denied. Do not retry them.
- You may only read files (source, tests, question) and write the single output file below.
- Derive the answer by reading the code and the test cases and reasoning about the execution
  step by step. Do not guess placeholder values; trace the program logic carefully.

Required workflow:
1. Open and read "$QFILE".
2. Use BOTH the "question" field and "template_answer" field.
3. The final output must follow template_answer exactly (same top-level keys, required structure, and value types).
4. Read the instance test cases under "$INSTANCE_DIR/files/tests/qa" and every referenced source file.
5. Mentally simulate the execution described by the tests to compute the correct answer.
6. Write ONLY the final JSON answer object to "$ANSWER_OUT".
7. Do not write markdown fences. Do not ask for confirmation.
8. Ensure "$ANSWER_OUT" is valid JSON before finishing.
EOF
)
        else
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
        fi

        : >"$RAW_TRAJ_OUT"
        cmd_status=0
        agent_timeout_s=600
        agent_kill_after_s=60
        if [[ -n "${CURSOR_API_KEY:-}" ]]; then
          if command -v timeout >/dev/null 2>&1; then
            timeout -k "${agent_kill_after_s}s" "${agent_timeout_s}s" cursor-agent --api-key "$CURSOR_API_KEY" -p --force --output-format stream-json --model "$MODEL" --workspace "$WORKSPACE" "$PROMPT" >"$RAW_TRAJ_OUT" 2>"$RUN_LOG" || cmd_status=$?
          else
            cursor-agent --api-key "$CURSOR_API_KEY" -p --force --output-format stream-json --model "$MODEL" --workspace "$WORKSPACE" "$PROMPT" >"$RAW_TRAJ_OUT" 2>"$RUN_LOG" || cmd_status=$?
          fi
        else
          if command -v timeout >/dev/null 2>&1; then
            timeout -k "${agent_kill_after_s}s" "${agent_timeout_s}s" cursor-agent -p --force --output-format stream-json --model "$MODEL" --workspace "$WORKSPACE" "$PROMPT" >"$RAW_TRAJ_OUT" 2>"$RUN_LOG" || cmd_status=$?
          else
            cursor-agent -p --force --output-format stream-json --model "$MODEL" --workspace "$WORKSPACE" "$PROMPT" >"$RAW_TRAJ_OUT" 2>"$RUN_LOG" || cmd_status=$?
          fi
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
          # No python in this container (e.g. --no-exec sandbox): leave traj.ndjson for the host to convert.
          :
        fi

        if (( cmd_status != 0 )); then
          printf "cursor-agent exited with status %s\n" "$cmd_status" >>"$RUN_LOG"
          if (( cmd_status == 124 )); then
            printf "cursor-agent timed out after %ss\n" "$agent_timeout_s" >>"$RUN_LOG"
          elif (( cmd_status == 137 )); then
            printf "cursor-agent was force-killed after timeout grace period (%ss)\n" "$agent_kill_after_s" >>"$RUN_LOG"
          fi
        fi

        if [[ -s "$TRAJ_OUT" ]]; then
          rm -f "$RAW_TRAJ_OUT"
        fi
      ' || true

    mkdir -p "$host_instance_out"
    if docker exec "$container_name" bash -lc "test -d '$container_repo_out/$instance_id'"; then
      # Files written by the container are root-owned; hand them to the host user (matters for the
      # bind-mounted output dir in --no-exec mode, harmless otherwise).
      docker exec "$container_name" bash -lc "chown -R $(id -u):$(id -g) '$container_repo_out/$instance_id'" >/dev/null 2>&1 || true
      docker cp "$container_name:$container_repo_out/$instance_id/." "$host_instance_out/" || true
      echo "[$repo][$((i + 1))/$LIMIT] persisted -> $host_instance_out"

      host_raw_traj="$host_instance_out/traj.ndjson"
      host_traj="$host_instance_out/traj.json"
      if [[ ! -s "$host_traj" && -s "$host_raw_traj" ]]; then
        host_py_bin="$(command -v python3 || command -v python || true)"
        if [[ -n "$host_py_bin" ]]; then
          "$host_py_bin" - "$host_raw_traj" "$host_traj" <<'PY'
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
          if [[ -s "$host_traj" ]]; then
            echo "[$repo][$((i + 1))/$LIMIT] recovered traj.json from traj.ndjson"
          else
            echo "[$repo][$((i + 1))/$LIMIT] WARN: failed to recover traj.json from traj.ndjson"
          fi
        else
          cp "$host_raw_traj" "$host_traj" || true
          echo "[$repo][$((i + 1))/$LIMIT] WARN: python not found; copied traj.ndjson to traj.json"
        fi
      fi
    else
      echo "[$repo][$((i + 1))/$LIMIT] WARN: no output dir produced for $instance_id"
    fi
  done

  echo "[$repo] Finished. Outputs were persisted instance-by-instance under: $host_repo_out"

  cleanup_repo
  trap - EXIT
done

echo
echo "Done. Outputs at: $HOST_MODEL_OUT"
