#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  evaluation_scripts/run_claude_code_eval_in_docker.sh --model <model> --repo <repo|all> [options]

Options:
  --model <model>              Claude model name (required)
  --repo <name|all>            Repo name from Repositories.json, or "all" (required)
  --num-instances <n>          Max instances per repo (default: all)
  --anthropic-api-key <key>    Anthropic API key (default: ANTHROPIC_API_KEY env var)
  --claude-extra-args "<args>" Extra args appended to claude command
  --no-auto-install            Do not auto-install missing Claude CLI in container
  --repos-file <path>          Path to repo->image map JSON (default: Repositories.json)
  --instances-root <path>      Host root for eval instances (default: qa_instances_eval)
  --output-root <path>         Host output root (default: evaluations/claude_code)
  --container-workdir <path>   Project dir inside container (default: /testbed)
  --resume                     Skip instances that already have non-empty answer.json
  --help                       Show help

Output layout:
  <output-root>/<model>/<repo>/<instance>/answer.json
  <output-root>/<model>/<repo>/<instance>/traj.json

Examples:
  ./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo Sympy
  ./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo all --num-instances 10
EOF
}

MODEL=""
REPO_ARG=""
NUM_INSTANCES="all"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
CLAUDE_EXTRA_ARGS=""
AUTO_INSTALL="1"
REPOS_FILE="$REPO_ROOT/Repositories.json"
INSTANCES_ROOT="$REPO_ROOT/qa_instances_eval"
OUTPUT_ROOT="$REPO_ROOT/evaluations/claude_code"
CONTAINER_WORKDIR="/testbed"
RESUME="0"

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
    --anthropic-api-key)
      ANTHROPIC_API_KEY="${2:-}"
      shift 2
      ;;
    --claude-extra-args)
      CLAUDE_EXTRA_ARGS="${2:-}"
      shift 2
      ;;
    --no-auto-install)
      AUTO_INSTALL="0"
      shift
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

if [[ -z "$ANTHROPIC_API_KEY" ]]; then
  echo "WARNING: ANTHROPIC_API_KEY is not set."
  echo "Claude CLI may fail in non-interactive container sessions without API key auth."
  echo "Set env var ANTHROPIC_API_KEY or pass --anthropic-api-key."
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
echo "Auto install:       $([[ "$AUTO_INSTALL" == "1" ]] && echo enabled || echo disabled)"
if [[ -n "$CLAUDE_EXTRA_ARGS" ]]; then
  echo "Claude extra args:  $CLAUDE_EXTRA_ARGS"
fi
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

  container_name="claude-code-eval-${repo,,}-${MODEL_DIR_NAME}-$$"
  container_repo_instances="$CONTAINER_WORKDIR/qa_instances_eval/$repo"
  container_repo_out="$CONTAINER_WORKDIR/evaluations/claude_code/$MODEL_DIR_NAME/$repo"
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

  cleanup_repo() {
    docker rm -f "$container_name" >/dev/null 2>&1 || true
  }
  trap cleanup_repo EXIT

  docker exec "$container_name" bash -lc "mkdir -p '$CONTAINER_WORKDIR/qa_instances_eval' '$container_repo_out'"
  docker cp "$host_repo_instances" "$container_name:$CONTAINER_WORKDIR/qa_instances_eval/"

  if ! docker exec \
    -e AUTO_INSTALL="$AUTO_INSTALL" \
    "$container_name" \
    bash -lc '
      set -euo pipefail
      export PATH="$HOME/.local/bin:$PATH"
      if command -v claude >/dev/null 2>&1; then
        exit 0
      fi

      if [[ "$AUTO_INSTALL" != "1" ]]; then
        echo "ERROR: claude CLI not found in container and auto-install is disabled." >&2
        exit 1
      fi

      # Preferred installer: native binary installer.
      if ! command -v curl >/dev/null 2>&1; then
        if command -v apt-get >/dev/null 2>&1; then
          export DEBIAN_FRONTEND=noninteractive
          apt-get update -y >/tmp/claude-apt-update.log 2>&1 || true
          apt-get install -y curl ca-certificates >/tmp/claude-apt-install.log 2>&1 || true
        elif command -v apk >/dev/null 2>&1; then
          apk add --no-cache curl ca-certificates >/tmp/claude-apk-install.log 2>&1 || true
        elif command -v dnf >/dev/null 2>&1; then
          dnf install -y curl ca-certificates >/tmp/claude-dnf-install.log 2>&1 || true
        elif command -v yum >/dev/null 2>&1; then
          yum install -y curl ca-certificates >/tmp/claude-yum-install.log 2>&1 || true
        fi
      fi

      if command -v curl >/dev/null 2>&1; then
        curl -fsSL https://claude.ai/install.sh | bash >/tmp/claude-native-install.log 2>&1 || true
      fi

      export PATH="$HOME/.local/bin:$PATH"
      if ! command -v claude >/dev/null 2>&1 && [[ -x "$HOME/.local/bin/claude" ]]; then
        mkdir -p /usr/local/bin >/dev/null 2>&1 || true
        ln -sf "$HOME/.local/bin/claude" /usr/local/bin/claude >/dev/null 2>&1 || true
      fi

      if command -v claude >/dev/null 2>&1; then
        exit 0
      fi

      # Fallback installer: npm package.
      if ! command -v npm >/dev/null 2>&1; then
        if command -v apt-get >/dev/null 2>&1; then
          export DEBIAN_FRONTEND=noninteractive
          apt-get update -y >/tmp/claude-apt-update.log 2>&1 || true
          apt-get install -y nodejs npm >/tmp/claude-apt-install.log 2>&1 || true
        elif command -v apk >/dev/null 2>&1; then
          apk add --no-cache nodejs npm >/tmp/claude-apk-install.log 2>&1 || true
        elif command -v dnf >/dev/null 2>&1; then
          dnf install -y nodejs npm >/tmp/claude-dnf-install.log 2>&1 || true
        elif command -v yum >/dev/null 2>&1; then
          yum install -y nodejs npm >/tmp/claude-yum-install.log 2>&1 || true
        fi
      fi

      if command -v npm >/dev/null 2>&1; then
        npm install -g @anthropic-ai/claude-code >/tmp/claude-npm-install.log 2>&1 || true
      fi

      export PATH="$HOME/.local/bin:$PATH"
      if ! command -v claude >/dev/null 2>&1; then
        echo "ERROR: failed to install Claude CLI in container." >&2
        echo "See /tmp/claude-native-install.log and /tmp/claude-npm-install.log for details." >&2
        exit 1
      fi
    '; then
    echo "[$repo] ERROR: Claude CLI is unavailable in container."
    cleanup_repo
    trap - EXIT
    continue
  fi

  echo "[$repo] Running $LIMIT instances..."
  for ((i = 0; i < LIMIT; i++)); do
    host_qfile="${QUESTION_FILES[$i]}"
    instance_id="$(basename "$(dirname "$host_qfile")")"
    qfile="$container_repo_instances/$instance_id/question.json"
    instance_dir="$container_repo_instances/$instance_id"
    answer_out="$container_repo_out/$instance_id/answer.json"
    run_log="$container_repo_out/$instance_id/claude.log"
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
      -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
      -e CLAUDE_EXTRA_ARGS="${CLAUDE_EXTRA_ARGS:-}" \
      "$container_name" \
      bash -lc '
        set -euo pipefail
        export PATH="$HOME/.local/bin:$PATH"
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

        cd "$WORKSPACE"
        : >"$RAW_TRAJ_OUT"
        cmd_status=0

        CLAUDE_CMD=(claude -p --verbose --output-format stream-json --model "$MODEL")
        if [[ "$(id -u)" -eq 0 ]]; then
          # Claude blocks bypassPermissions for root/sudo. Use root-safe non-interactive permissions.
          CLAUDE_CMD+=(--permission-mode acceptEdits --allowedTools "Bash(*)")
        else
          CLAUDE_CMD+=(--dangerously-skip-permissions)
        fi
        if [[ -n "${CLAUDE_EXTRA_ARGS:-}" ]]; then
          # shellcheck disable=SC2206
          extra_args=( ${CLAUDE_EXTRA_ARGS} )
          CLAUDE_CMD+=("${extra_args[@]}")
        fi
        CLAUDE_CMD+=(-- "$PROMPT")

        "${CLAUDE_CMD[@]}" >"$RAW_TRAJ_OUT" 2>"$RUN_LOG" || cmd_status=$?

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
          printf "claude exited with status %s\n" "$cmd_status" >>"$RUN_LOG"
        fi

        rm -f "$RAW_TRAJ_OUT"
      ' || true

    mkdir -p "$host_instance_out"
    if docker exec "$container_name" bash -lc "test -d '$container_repo_out/$instance_id'"; then
      docker cp "$container_name:$container_repo_out/$instance_id/." "$host_instance_out/" || true
      echo "[$repo][$((i + 1))/$LIMIT] persisted -> $host_instance_out"
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
