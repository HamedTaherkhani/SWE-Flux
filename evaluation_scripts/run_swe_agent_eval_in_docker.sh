#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  evaluation_scripts/run_swe_agent_eval_in_docker.sh --agent <swe-agent|mini-swe-agent> --model <model> --repo <repo|all> [options]

Options:
  --agent <name>               Agent to run: swe-agent | mini-swe-agent (required)
  --model <model>              Model name passed to selected agent (required)
  --repo <name|all>            Repo name from Repositories.json, or "all" (required)
  --num-instances <n>          Max instances per repo (default: all)
  --agent-extra-args "<args>"  Extra args appended to selected agent command
  --repos-file <path>          Path to repo->image map JSON (default: Repositories.json)
  --instances-root <path>      Host root for eval instances (default: qa_instances_eval)
  --output-root <path>         Host base output root (default: evaluations)
  --container-workdir <path>   Project dir inside container (default: /testbed)
  --openai-api-key <key>       OpenAI API key (default: OPENAI_API_KEY env)
  --anthropic-api-key <key>    Anthropic API key (default: ANTHROPIC_API_KEY env)
  --google-api-key <key>       Google API key (default: GOOGLE_API_KEY env)
  --gemini-api-key <key>       Gemini API key (default: GEMINI_API_KEY env)
  --openrouter-api-key <key>   OpenRouter API key (default: OPENROUTER_API_KEY env)
  --no-auto-install            Do not auto-install missing agent CLI in container
  --resume                     Skip instances that already have non-empty answer.json
  --help                       Show help

Output layout:
  evaluations/<agent>/<model>/<repo>/<instance>/answer.json

Examples:
  ./evaluation_scripts/run_swe_agent_eval_in_docker.sh --agent swe-agent --model gpt-5 --repo Sympy
  ./evaluation_scripts/run_swe_agent_eval_in_docker.sh --agent mini-swe-agent --model openai/gpt-4.1 --repo all --num-instances 10
EOF
}

normalize_agent() {
  local v="${1:-}"
  case "${v,,}" in
    swe-agent|sweagent|swe)
      printf '%s' "swe-agent"
      ;;
    mini-swe-agent|mini_swe_agent|mini-swe|mini|mswea)
      printf '%s' "mini-swe-agent"
      ;;
    *)
      return 1
      ;;
  esac
}

infer_repo_subdir_from_question() {
  local question_file="$1"
  jq -r '.question // ""' "$question_file" \
    | sed -nE 's#.*(/testbed/([A-Za-z0-9_.-]+)/).*#\2#p' \
    | head -n1
}

AGENT_RAW=""
AGENT=""
MODEL=""
REPO_ARG=""
NUM_INSTANCES="all"
AGENT_EXTRA_ARGS=""
REPOS_FILE="$REPO_ROOT/Repositories.json"
INSTANCES_ROOT="$REPO_ROOT/qa_instances_eval"
OUTPUT_ROOT="$REPO_ROOT/evaluations"
CONTAINER_WORKDIR="/testbed"
AUTO_INSTALL="1"
RESUME="0"

OPENAI_API_KEY="${OPENAI_API_KEY:-}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
GOOGLE_API_KEY="${GOOGLE_API_KEY:-}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent)
      AGENT_RAW="${2:-}"
      shift 2
      ;;
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
    --agent-extra-args)
      AGENT_EXTRA_ARGS="${2:-}"
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
    --openai-api-key)
      OPENAI_API_KEY="${2:-}"
      shift 2
      ;;
    --anthropic-api-key)
      ANTHROPIC_API_KEY="${2:-}"
      shift 2
      ;;
    --google-api-key)
      GOOGLE_API_KEY="${2:-}"
      shift 2
      ;;
    --gemini-api-key)
      GEMINI_API_KEY="${2:-}"
      shift 2
      ;;
    --openrouter-api-key)
      OPENROUTER_API_KEY="${2:-}"
      shift 2
      ;;
    --no-auto-install)
      AUTO_INSTALL="0"
      shift
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

if [[ -z "$AGENT_RAW" || -z "$MODEL" || -z "$REPO_ARG" ]]; then
  echo "ERROR: --agent, --model, and --repo are required." >&2
  usage
  exit 1
fi

if ! AGENT="$(normalize_agent "$AGENT_RAW")"; then
  echo "ERROR: unsupported --agent '$AGENT_RAW'. Use swe-agent or mini-swe-agent." >&2
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

MODEL_DIR_NAME="$(printf '%s' "$MODEL" | sed 's#[/[:space:]]#_#g')"
HOST_MODEL_OUT="$OUTPUT_ROOT/$AGENT/$MODEL_DIR_NAME"
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

echo "Agent:               $AGENT"
echo "Model:               $MODEL"
echo "Model output root:   $HOST_MODEL_OUT"
echo "Repos file:          $REPOS_FILE"
echo "Target repos:        ${TARGET_REPOS[*]}"
echo "Instances root:      $INSTANCES_ROOT"
echo "Container workdir:   $CONTAINER_WORKDIR"
echo "Resume mode:         $([[ "$RESUME" == "1" ]] && echo enabled || echo disabled)"
echo "Auto install agent:  $([[ "$AUTO_INSTALL" == "1" ]] && echo enabled || echo disabled)"
if [[ -n "$AGENT_EXTRA_ARGS" ]]; then
  echo "Agent extra args:    $AGENT_EXTRA_ARGS"
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

  repo_subdir="$(infer_repo_subdir_from_question "${QUESTION_FILES[0]}")"
  container_name="agent-eval-${AGENT//[^a-zA-Z0-9]/-}-${repo,,}-${MODEL_DIR_NAME}-$$"
  container_repo_instances="$CONTAINER_WORKDIR/qa_instances_eval/$repo"
  container_repo_out="$CONTAINER_WORKDIR/evaluations/$AGENT/$MODEL_DIR_NAME/$repo"
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

  container_repo_root="$(
    docker exec \
      -e WORKDIR="$CONTAINER_WORKDIR" \
      -e REPO_SUBDIR="${repo_subdir:-}" \
      "$container_name" \
      bash -lc '
        set -euo pipefail
        if [[ -n "${REPO_SUBDIR:-}" && -d "$WORKDIR/$REPO_SUBDIR" ]]; then
          printf "%s" "$WORKDIR/$REPO_SUBDIR"
          exit 0
        fi

        if [[ -f "$WORKDIR/pyproject.toml" || -f "$WORKDIR/setup.py" || -f "$WORKDIR/setup.cfg" || -d "$WORKDIR/.git" ]]; then
          printf "%s" "$WORKDIR"
          exit 0
        fi

        mapfile -t dirs < <(find "$WORKDIR" -mindepth 1 -maxdepth 1 -type d | sort)
        if (( ${#dirs[@]} == 1 )); then
          printf "%s" "${dirs[0]}"
        else
          printf "%s" "$WORKDIR"
        fi
      '
  )"
  echo "[$repo] Repo root in container: $container_repo_root"

  if ! docker exec \
    -e AGENT="$AGENT" \
    -e AUTO_INSTALL="$AUTO_INSTALL" \
    "$container_name" \
    bash -lc '
      set -euo pipefail

      if [[ "$AGENT" == "mini-swe-agent" ]]; then
        if command -v mini >/dev/null 2>&1 || command -v mini-swe-agent >/dev/null 2>&1; then
          exit 0
        fi

        if [[ "$AUTO_INSTALL" != "1" ]]; then
          echo "ERROR: mini/mini-swe-agent not found in container and auto-install is disabled." >&2
          exit 1
        fi

        py="$(command -v python3 || command -v python || true)"
        if [[ -z "$py" ]]; then
          echo "ERROR: python/python3 not found in container; cannot install mini-swe-agent." >&2
          exit 1
        fi

        if ! "$py" -m pip --version >/dev/null 2>&1; then
          "$py" -m ensurepip --upgrade >/dev/null 2>&1 || true
        fi

        # First attempt: direct install (works when container Python is >=3.10).
        if "$py" -m pip install --quiet --disable-pip-version-check mini-swe-agent >/tmp/mini-pip-install.log 2>&1 \
          && (command -v mini >/dev/null 2>&1 || command -v mini-swe-agent >/dev/null 2>&1); then
          exit 0
        fi

        # Fallback for old benchmark images (often Python 3.8/3.9):
        # install uv and run mini-swe-agent with a managed Python 3.12 via uvx.
        "$py" -m pip install --quiet --disable-pip-version-check uv
        if ! command -v uvx >/dev/null 2>&1; then
          echo "ERROR: failed to install uvx fallback for mini-swe-agent." >&2
          exit 1
        fi
        exit 0
      else
        cmd="sweagent"
        pkg="sweagent"

        if command -v "$cmd" >/dev/null 2>&1; then
          exit 0
        fi

        if [[ "$AUTO_INSTALL" != "1" ]]; then
          echo "ERROR: $cmd not found in container and auto-install is disabled." >&2
          exit 1
        fi

        py="$(command -v python3 || command -v python || true)"
        if [[ -z "$py" ]]; then
          echo "ERROR: python/python3 not found in container; cannot install $pkg." >&2
          exit 1
        fi

        if ! "$py" -m pip --version >/dev/null 2>&1; then
          "$py" -m ensurepip --upgrade >/dev/null 2>&1 || true
        fi

        if ! "$py" -m pip install --quiet --disable-pip-version-check "$pkg"; then
          py_ver="$("$py" - <<PY
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
PY
)"
          echo "ERROR: failed to install $pkg in container (python=$py_ver)." >&2
          echo "SWE-agent currently requires Python >=3.11 in most recent releases." >&2
          exit 1
        fi

        if ! command -v "$cmd" >/dev/null 2>&1; then
          echo "ERROR: failed to install $pkg in container." >&2
          exit 1
        fi
        exit 0
      fi
    '; then
    echo "[$repo] ERROR: selected agent CLI is unavailable in container."
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

    if [[ "$AGENT" == "mini-swe-agent" ]]; then
      run_log="$container_repo_out/$instance_id/mini.log"
      traj_out="$container_repo_out/$instance_id/mini.traj.json"
      swe_output_dir=""
    else
      run_log="$container_repo_out/$instance_id/sweagent.log"
      traj_out=""
      swe_output_dir="$container_repo_out/$instance_id/sweagent_output"
    fi

    host_instance_out="$host_repo_out/$instance_id"
    host_answer="$host_instance_out/answer.json"

    if [[ "$RESUME" == "1" && -s "$host_answer" ]]; then
      echo "[$repo][$((i + 1))/$LIMIT] $instance_id (skip: answer exists)"
      continue
    fi

    echo "[$repo][$((i + 1))/$LIMIT] $instance_id"

    docker exec \
      -e AGENT="$AGENT" \
      -e MODEL="$MODEL" \
      -e QFILE="$qfile" \
      -e INSTANCE_ID="$instance_id" \
      -e INSTANCE_DIR="$instance_dir" \
      -e ANSWER_OUT="$answer_out" \
      -e RUN_LOG="$run_log" \
      -e TRAJ_OUT="$traj_out" \
      -e SWE_OUTPUT_DIR="$swe_output_dir" \
      -e REPO_PATH="$container_repo_root" \
      -e AGENT_EXTRA_ARGS="$AGENT_EXTRA_ARGS" \
      -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
      -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
      -e GOOGLE_API_KEY="${GOOGLE_API_KEY:-}" \
      -e GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
      -e OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}" \
      -e MSWEA_CONFIGURED="true" \
      "$container_name" \
      bash -lc '
        set -euo pipefail
        mkdir -p "$(dirname "$ANSWER_OUT")"

        PROMPT=$(cat <<EOF
You are running a repository QA evaluation instance with full environment access.

Question file: $QFILE
Instance directory: $INSTANCE_DIR
Repository root: $REPO_PATH
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
9. After writing "$ANSWER_OUT", finish your run immediately.
EOF
)

        EXTRA_ARGS=()
        if [[ -n "${AGENT_EXTRA_ARGS:-}" ]]; then
          # shellcheck disable=SC2206
          EXTRA_ARGS=(${AGENT_EXTRA_ARGS})
        fi

        if [[ "$AGENT" == "mini-swe-agent" ]]; then
          cd "$REPO_PATH"
          export MSWEA_CONFIGURED="${MSWEA_CONFIGURED:-true}"
          MINI_CMD=()
          if command -v mini >/dev/null 2>&1; then
            MINI_CMD=(mini)
          elif command -v mini-swe-agent >/dev/null 2>&1; then
            MINI_CMD=(mini-swe-agent)
          elif command -v uvx >/dev/null 2>&1; then
            MINI_CMD=(uvx --python 3.12 mini-swe-agent)
          else
            echo "mini-swe-agent CLI is unavailable (mini/mini-swe-agent/uvx not found)." >&2
            exit 1
          fi

          "${MINI_CMD[@]}" \
            -y \
            --exit-immediately \
            --environment-class local \
            -m "$MODEL" \
            -o "$TRAJ_OUT" \
            -t "$PROMPT" \
            "${EXTRA_ARGS[@]}" \
            >"$RUN_LOG" 2>&1
        else
          sweagent run \
            --agent.model.name="$MODEL" \
            --env.deployment.type=local \
            --env.repo.path="$REPO_PATH" \
            --problem_statement.type=text \
            --problem_statement.id="$INSTANCE_ID" \
            --problem_statement.text="$PROMPT" \
            --output_dir="$SWE_OUTPUT_DIR" \
            "${EXTRA_ARGS[@]}" \
            >"$RUN_LOG" 2>&1
        fi
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
