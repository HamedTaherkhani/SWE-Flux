#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  evaluation_scripts/run_codex_eval_in_docker.sh --model <model> --repo <repo|all> [options]

Runs OpenAI Codex CLI (`codex exec`) on QA instances inside the repository Docker images.

Options:
  --model <model>              Codex model name (required, e.g. gpt-5.4, gpt-5.3-codex)
  --repo <name|all>            Repo name from Repositories.json, or "all" (required)
  --num-instances <n>          Max instances per repo (default: all)
  --reasoning-effort <lvl>     Codex model_reasoning_effort (low|medium|high|xhigh; default: unset)
  --model-dir <name>           Output folder name under <output-root> (default: <model>[-<effort>])
  --codex-bin <path>           Host codex binary to copy into the container
                               (default: `codex` on PATH, else newest Cursor-bundled codex)
  --openai-api-key <key>       Authenticate with an API key (default: OPENAI_API_KEY / openai_api_key env,
                               then openai_api_key in <repo>/.env). Preferred over the ChatGPT auth file.
  --codex-auth-file <path>     Authenticate with a ChatGPT-plan auth.json (default: ~/.codex/auth.json).
                               Used only when no API key is available.
  --repos-file <path>          Path to repo->image map JSON (default: Repositories.json)
  --instances-root <path>      Host root for eval instances (default: qa_instances_eval)
  --output-root <path>         Host output root (default: evaluations/codex, or evaluations/codex-noexec with --no-exec)
  --container-workdir <path>   Project dir inside container (default: /testbed)
  --timeout <seconds>          Per-instance agent timeout (default: 600)
  --parallel <n>               Run up to n instances concurrently per repo (default: 1)
  --resume                     Skip instances that already have non-empty answer.json
  --no-exec                    Static mode: the agent gets a READ-ONLY copy of the repo inside a
                               minimal sandbox image with NO python / pytest / project environment.
                               The shell remains available only for reading files (cat, sed, grep, rg).
  --sandbox-image <image>      Base image for --no-exec sandbox (default: ubuntu:22.04)
  --help                       Show help

Output layout:
  <output-root>/<model>/<repo>/<instance>/answer.json
  <output-root>/<model>/<repo>/<instance>/traj.json         (codex --json events)
  <output-root>/<model>/<repo>/<instance>/codex.log
  <output-root>/<model>/<repo>/<instance>/last_message.txt

Examples:
  ./evaluation_scripts/run_codex_eval_in_docker.sh --model gpt-5.4 --repo Sympy
  ./evaluation_scripts/run_codex_eval_in_docker.sh --model gpt-5.4 --repo all --num-instances 10 --no-exec
EOF
}

MODEL=""
REPO_ARG=""
NUM_INSTANCES="all"
REASONING_EFFORT=""
MODEL_DIR_OVERRIDE=""
CODEX_BIN=""
OPENAI_API_KEY="${OPENAI_API_KEY:-${openai_api_key:-}}"
CODEX_AUTH_FILE="${HOME}/.codex/auth.json"
REPOS_FILE="$REPO_ROOT/Repositories.json"
INSTANCES_ROOT="$REPO_ROOT/qa_instances_eval"
OUTPUT_ROOT=""
CONTAINER_WORKDIR="/testbed"
AGENT_TIMEOUT_S=600
PARALLEL=1
RESUME="0"
NO_EXEC="0"
SANDBOX_IMAGE="ubuntu:22.04"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) MODEL="${2:-}"; shift 2 ;;
    --repo) REPO_ARG="${2:-}"; shift 2 ;;
    --num-instances) NUM_INSTANCES="${2:-}"; shift 2 ;;
    --reasoning-effort) REASONING_EFFORT="${2:-}"; shift 2 ;;
    --model-dir) MODEL_DIR_OVERRIDE="${2:-}"; shift 2 ;;
    --codex-bin) CODEX_BIN="${2:-}"; shift 2 ;;
    --openai-api-key) OPENAI_API_KEY="${2:-}"; shift 2 ;;
    --codex-auth-file) CODEX_AUTH_FILE="${2:-}"; shift 2 ;;
    --repos-file) REPOS_FILE="${2:-}"; shift 2 ;;
    --instances-root) INSTANCES_ROOT="${2:-}"; shift 2 ;;
    --output-root) OUTPUT_ROOT="${2:-}"; shift 2 ;;
    --container-workdir) CONTAINER_WORKDIR="${2:-}"; shift 2 ;;
    --timeout) AGENT_TIMEOUT_S="${2:-}"; shift 2 ;;
    --parallel) PARALLEL="${2:-}"; shift 2 ;;
    --resume) RESUME="1"; shift ;;
    --no-exec) NO_EXEC="1"; shift ;;
    --sandbox-image) SANDBOX_IMAGE="${2:-}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$MODEL" || -z "$REPO_ARG" ]]; then
  echo "ERROR: --model and --repo are required." >&2
  usage
  exit 1
fi

if [[ -z "$OUTPUT_ROOT" ]]; then
  if [[ "$NO_EXEC" == "1" ]]; then
    OUTPUT_ROOT="$REPO_ROOT/evaluations/codex-noexec"
  else
    OUTPUT_ROOT="$REPO_ROOT/evaluations/codex"
  fi
fi
TOOL_DIR_NAME="$(basename "$OUTPUT_ROOT")"

if [[ ! -f "$REPOS_FILE" ]]; then
  echo "ERROR: repos file not found: $REPOS_FILE" >&2
  exit 1
fi
if [[ "$NUM_INSTANCES" != "all" ]] && ! [[ "$NUM_INSTANCES" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --num-instances must be a non-negative integer or 'all'." >&2
  exit 1
fi
if ! [[ "$AGENT_TIMEOUT_S" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --timeout must be an integer number of seconds." >&2
  exit 1
fi
if ! [[ "$PARALLEL" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR: --parallel must be a positive integer." >&2
  exit 1
fi
for tool in jq docker; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "ERROR: $tool is required." >&2
    exit 1
  fi
done

# Locate the codex binary on the host (static binary, copied into each container).
if [[ -z "$CODEX_BIN" ]]; then
  if command -v codex >/dev/null 2>&1; then
    CODEX_BIN="$(readlink -f "$(command -v codex)")"
  else
    CODEX_BIN="$(ls -1d "$HOME"/.cursor/extensions/openai.chatgpt-*/bin/linux-x86_64/codex 2>/dev/null | sort -V | tail -n 1 || true)"
  fi
fi
if [[ -z "$CODEX_BIN" || ! -x "$CODEX_BIN" ]]; then
  echo "ERROR: codex binary not found. Install Codex CLI or pass --codex-bin <path>." >&2
  exit 1
fi
CODEX_BIN_DIR="$(dirname "$CODEX_BIN")"
CODEX_RG_BIN=""
if [[ -x "$CODEX_BIN_DIR/rg" ]]; then
  CODEX_RG_BIN="$CODEX_BIN_DIR/rg"
elif command -v rg >/dev/null 2>&1; then
  CODEX_RG_BIN="$(readlink -f "$(command -v rg)")"
fi

# Fall back to the repo-root .env (openai_api_key=... / OPENAI_API_KEY=...) when no key is in the env.
if [[ -z "$OPENAI_API_KEY" && -f "$REPO_ROOT/.env" ]]; then
  OPENAI_API_KEY="$(grep -E '^(export )?(openai_api_key|OPENAI_API_KEY)=' "$REPO_ROOT/.env" | tail -n 1 | sed -E 's/^(export )?[^=]+=//; s/^["'"'"']//; s/["'"'"']$//' || true)"
fi

AUTH_MODE="none"
if [[ -n "$OPENAI_API_KEY" ]]; then
  AUTH_MODE="api-key"
elif [[ -f "$CODEX_AUTH_FILE" ]]; then
  AUTH_MODE="auth-file"
else
  echo "ERROR: no authentication available. Pass --openai-api-key or provide $CODEX_AUTH_FILE." >&2
  exit 1
fi

MODEL_DIR_NAME="$(printf '%s' "$MODEL" | sed 's#[/[:space:]]#_#g')"
if [[ -n "$REASONING_EFFORT" ]]; then
  MODEL_DIR_NAME="${MODEL_DIR_NAME}-${REASONING_EFFORT}"
fi
if [[ -n "$MODEL_DIR_OVERRIDE" ]]; then
  MODEL_DIR_NAME="$MODEL_DIR_OVERRIDE"
fi
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

HOST_PY_BIN="$(command -v python3 || command -v python || true)"

convert_ndjson_to_json() {
  # $1 = traj.ndjson, $2 = traj.json
  local src="$1" dst="$2"
  if [[ -n "$HOST_PY_BIN" ]]; then
    "$HOST_PY_BIN" - "$src" "$dst" <<'PY'
import json
import sys

src, dst = sys.argv[1], sys.argv[2]
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
    cp "$src" "$dst"
  fi
}

echo "Model:              $MODEL"
echo "Reasoning effort:   ${REASONING_EFFORT:-default}"
echo "Codex binary:       $CODEX_BIN ($("$CODEX_BIN" --version 2>/dev/null || echo unknown))"
echo "Auth:               $AUTH_MODE"
echo "Model output root:  $HOST_MODEL_OUT"
echo "Repos file:         $REPOS_FILE"
echo "Target repos:       ${TARGET_REPOS[*]}"
echo "Instances root:     $INSTANCES_ROOT"
echo "Container workdir:  $CONTAINER_WORKDIR"
echo "Timeout/instance:   ${AGENT_TIMEOUT_S}s"
echo "Parallel instances: $PARALLEL"
echo "Resume mode:        $([[ "$RESUME" == "1" ]] && echo enabled || echo disabled)"
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

  container_name="codex-eval-${repo,,}-${MODEL_DIR_NAME}-$$"
  container_repo_instances="$CONTAINER_WORKDIR/qa_instances_eval/$repo"
  container_repo_out="$CONTAINER_WORKDIR/evaluations/$TOOL_DIR_NAME/$MODEL_DIR_NAME/$repo"
  host_repo_out="$HOST_MODEL_OUT/$repo"
  mkdir -p "$host_repo_out"

  if [[ "$RESUME" == "1" ]]; then
    pending=0
    for ((i = 0; i < LIMIT; i++)); do
      instance_id="$(basename "$(dirname "${QUESTION_FILES[$i]}")")"
      if [[ ! -s "$host_repo_out/$instance_id/answer.json" ]]; then
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
    snapshot_dir="$(mktemp -d "${TMPDIR:-/tmp}/codex-noexec-${repo,,}-XXXXXX")"
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

  # Install the codex bundle into the container. Codex expects sibling helpers such as
  # codex-code-mode-host next to its own executable, so copy the whole bundle directory and
  # expose it through a wrapper (current_exe resolves to /opt/codex/codex).
  docker exec "$container_name" bash -lc "mkdir -p /opt/codex"
  docker cp "$CODEX_BIN_DIR/." "$container_name:/opt/codex/"
  docker exec "$container_name" bash -lc "cat >/usr/local/bin/codex <<'EOF'
#!/usr/bin/env bash
exec /opt/codex/$(basename "$CODEX_BIN") \"\$@\"
EOF
chmod +x /usr/local/bin/codex /opt/codex/* 2>/dev/null || true
if [[ -x /opt/codex/rg && ! -e /usr/local/bin/rg ]]; then ln -s /opt/codex/rg /usr/local/bin/rg; fi"
  if [[ -n "$CODEX_RG_BIN" && ! -x "$CODEX_BIN_DIR/rg" ]]; then
    docker cp "$CODEX_RG_BIN" "$container_name:/usr/local/bin/rg"
  fi
  if ! docker exec "$container_name" bash -lc "codex --version >/dev/null 2>&1"; then
    echo "[$repo] ERROR: codex binary does not run inside the container." >&2
    cleanup_repo
    trap - EXIT
    continue
  fi

  # Codex home: config + auth. Kept outside the (possibly read-only) workspace.
  container_codex_home="/root/.codex"
  # web_search is disabled so the agent can only use the repository (no external lookups).
  # model_reasoning_summary makes Codex emit the model's reasoning summaries as `reasoning`
  # items in the --json stream (and hence traj.json); without it some models log none.
  config_toml="model = \"$MODEL\"
approval_policy = \"never\"
sandbox_mode = \"danger-full-access\"
web_search = \"disabled\"
model_reasoning_summary = \"detailed\"
show_raw_agent_reasoning = true
"
  if [[ -n "$REASONING_EFFORT" ]]; then
    config_toml+="model_reasoning_effort = \"$REASONING_EFFORT\"
"
  fi
  config_toml+="
[projects.\"$CONTAINER_WORKDIR\"]
trust_level = \"trusted\"
"
  docker exec "$container_name" bash -lc "mkdir -p '$container_codex_home'"
  printf '%s' "$config_toml" | docker exec -i "$container_name" bash -lc "cat > '$container_codex_home/config.toml'"

  if [[ "$AUTH_MODE" == "api-key" ]]; then
    printf '%s' "$OPENAI_API_KEY" | docker exec -i -e CODEX_HOME="$container_codex_home" "$container_name" bash -lc "codex login --with-api-key" >/dev/null 2>&1 || {
      echo "[$repo] ERROR: codex login --with-api-key failed." >&2
      cleanup_repo
      trap - EXIT
      continue
    }
  else
    docker cp "$CODEX_AUTH_FILE" "$container_name:$container_codex_home/auth.json"
  fi
  echo "[$repo] Codex auth status: $(docker exec -e CODEX_HOME="$container_codex_home" "$container_name" bash -lc 'codex login status 2>&1 | head -n 1' || true)"

  run_one_instance() {
    local i="$1"
    host_qfile="${QUESTION_FILES[$i]}"
    instance_id="$(basename "$(dirname "$host_qfile")")"
    qfile="$container_repo_instances/$instance_id/question.json"
    instance_dir="$container_repo_instances/$instance_id"
    answer_out="$container_repo_out/$instance_id/answer.json"
    host_instance_out="$host_repo_out/$instance_id"
    host_answer="$host_instance_out/answer.json"

    if [[ "$RESUME" == "1" && -s "$host_answer" ]]; then
      echo "[$repo][$((i + 1))/$LIMIT] $instance_id (skip: answer exists)"
      return 0
    fi
    echo "[$repo][$((i + 1))/$LIMIT] $instance_id"

    docker exec \
      -e MODEL="$MODEL" \
      -e QFILE="$qfile" \
      -e INSTANCE_DIR="$instance_dir" \
      -e ANSWER_OUT="$answer_out" \
      -e WORKSPACE="$CONTAINER_WORKDIR" \
      -e NO_EXEC="$NO_EXEC" \
      -e AGENT_TIMEOUT_S="$AGENT_TIMEOUT_S" \
      -e CODEX_HOME="$container_codex_home" \
      "$container_name" \
      bash -lc '
        set -euo pipefail
        OUT_DIR="$(dirname "$ANSWER_OUT")"
        mkdir -p "$OUT_DIR"
        RAW_TRAJ_OUT="$OUT_DIR/traj.ndjson"
        RUN_LOG="$OUT_DIR/codex.log"
        LAST_MSG="$OUT_DIR/last_message.txt"

        if [[ "$NO_EXEC" == "1" ]]; then
        PROMPT=$(cat <<EOF
You are running a repository QA evaluation instance in STATIC mode (no code execution).

Question file: $QFILE
Instance directory: $INSTANCE_DIR
Output file to write: $ANSWER_OUT

Constraints of this environment:
- The repository is mounted READ-ONLY and there is NO Python interpreter, pytest, or project
  environment installed. You CANNOT run the tests or execute any project code.
- Use the shell ONLY to read files (cat, sed -n, grep, rg, ls, find). Attempts to run python,
  pytest, or the project will fail; do not waste steps retrying them.
- The only writable location is "$OUT_DIR".
- Derive the answer by reading the code and the test cases and reasoning about the execution
  step by step. Do not guess placeholder values; trace the program logic carefully.

Required workflow:
1. Read "$QFILE".
2. Use BOTH the "question" field and "template_answer" field.
3. The final output must follow template_answer exactly (same top-level keys, required structure, and value types).
4. Read the instance test cases under "$INSTANCE_DIR/files/tests/qa" and every referenced source file.
5. Mentally simulate the execution described by the tests to compute the correct answer.
6. Write ONLY the final JSON answer object to "$ANSWER_OUT" (e.g. with a shell heredoc).
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
        : >"$RUN_LOG"
        cmd_status=0
        kill_after_s=60
        # The container is the sandbox, so Codex'"'"'s own sandbox/approvals are bypassed.
        codex_cmd=(codex exec --json --ephemeral --skip-git-repo-check \
          --dangerously-bypass-approvals-and-sandbox \
          -C "$WORKSPACE" -m "$MODEL" -o "$LAST_MSG" "$PROMPT")
        if command -v timeout >/dev/null 2>&1; then
          timeout -k "${kill_after_s}s" "${AGENT_TIMEOUT_S}s" "${codex_cmd[@]}" </dev/null >"$RAW_TRAJ_OUT" 2>"$RUN_LOG" || cmd_status=$?
        else
          "${codex_cmd[@]}" </dev/null >"$RAW_TRAJ_OUT" 2>"$RUN_LOG" || cmd_status=$?
        fi

        if (( cmd_status != 0 )); then
          printf "codex exited with status %s\n" "$cmd_status" >>"$RUN_LOG"
          if (( cmd_status == 124 )); then
            printf "codex timed out after %ss\n" "$AGENT_TIMEOUT_S" >>"$RUN_LOG"
          elif (( cmd_status == 137 )); then
            printf "codex was force-killed after timeout grace period (%ss)\n" "$kill_after_s" >>"$RUN_LOG"
          fi
        fi
      ' || true

    mkdir -p "$host_instance_out"
    if docker exec "$container_name" bash -lc "test -d '$container_repo_out/$instance_id'"; then
      # Files written by the container are root-owned; hand them to the host user (matters for the
      # bind-mounted output dir in --no-exec mode, harmless otherwise).
      docker exec "$container_name" bash -lc "chown -R $(id -u):$(id -g) '$container_repo_out/$instance_id'" >/dev/null 2>&1 || true
      docker cp "$container_name:$container_repo_out/$instance_id/." "$host_instance_out/" || true
      if [[ -s "$host_instance_out/traj.ndjson" ]]; then
        convert_ndjson_to_json "$host_instance_out/traj.ndjson" "$host_instance_out/traj.json"
        if [[ -s "$host_instance_out/traj.json" ]]; then
          rm -f "$host_instance_out/traj.ndjson"
        fi
      fi
      if [[ -s "$host_answer" ]]; then
        echo "[$repo][$((i + 1))/$LIMIT] persisted -> $host_instance_out"
      else
        echo "[$repo][$((i + 1))/$LIMIT] WARN: no answer.json produced (see codex.log)"
      fi
    else
      echo "[$repo][$((i + 1))/$LIMIT] WARN: no output dir produced for $instance_id"
    fi
  }

  echo "[$repo] Running $LIMIT instances (parallel=$PARALLEL)..."
  running=0
  for ((i = 0; i < LIMIT; i++)); do
    if (( PARALLEL <= 1 )); then
      run_one_instance "$i"
      continue
    fi
    run_one_instance "$i" &
    running=$((running + 1))
    if (( running >= PARALLEL )); then
      wait -n || true
      running=$((running - 1))
    fi
  done
  wait || true

  echo "[$repo] Finished. Outputs under: $host_repo_out"
  cleanup_repo
  trap - EXIT
done

echo
echo "Done. Outputs at: $HOST_MODEL_OUT"
