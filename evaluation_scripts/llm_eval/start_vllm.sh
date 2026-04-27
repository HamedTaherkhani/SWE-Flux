#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VLLM_MODEL="${VLLM_MODEL:-}"
if [[ -n "${VLLM_ALIAS:-}" ]]; then
  VLLM_ALIAS="$VLLM_ALIAS"
elif [[ -n "${VLLM_MODEL:-}" ]]; then
  VLLM_ALIAS="$(basename "$VLLM_MODEL")"
else
  VLLM_ALIAS="local-vllm"
fi
VLLM_HOST="${VLLM_HOST:-0.0.0.0}"
VLLM_CLIENT_HOST="${VLLM_CLIENT_HOST:-127.0.0.1}"
VLLM_PORT="${VLLM_PORT:-8000}"
VLLM_TP="${VLLM_TP:-2}"
VLLM_DTYPE="${VLLM_DTYPE:-bfloat16}"
VLLM_GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.9}"
VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-30910}"
VLLM_MAX_NUM_BATCHED_TOKENS="${VLLM_MAX_NUM_BATCHED_TOKENS:-30910}"
VLLM_MAX_NUM_SEQS="${VLLM_MAX_NUM_SEQS:-1}"
VLLM_ENFORCE_EAGER="${VLLM_ENFORCE_EAGER:-1}"
VLLM_KV_CACHE_DTYPE="${VLLM_KV_CACHE_DTYPE:-fp8}"
VLLM_ENABLE_AUTO_TOOL_CHOICE="${VLLM_ENABLE_AUTO_TOOL_CHOICE:-1}"
VLLM_TOOL_CALL_PARSER="${VLLM_TOOL_CALL_PARSER:-gemma4}"
VLLM_HEALTH_TIMEOUT_SECONDS="${VLLM_HEALTH_TIMEOUT_SECONDS:-300}"

LOG_FILE="${VLLM_LOG_FILE:-$SCRIPT_DIR/vllm_server.log}"
PID_FILE="${VLLM_PID_FILE:-$SCRIPT_DIR/.vllm_server.pid}"



# Helps reduce fragmentation during long runs.
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

health_url() {
  echo "http://${VLLM_CLIENT_HOST}:${VLLM_PORT}/health"
}

api_base_url() {
  echo "http://${VLLM_CLIENT_HOST}:${VLLM_PORT}/v1"
}

usage() {
  cat <<'EOF'
Usage:
  start_vllm.sh start [vllm_server_args...]
  start_vllm.sh serve [vllm_server_args...]
  start_vllm.sh stop
  start_vllm.sh status
  start_vllm.sh logs [tail_args...]

This script only manages the local vLLM server lifecycle.
Run evaluation separately with:
  python3 evaluation_scripts/llm_eval/run_llm_repomap_eval_host.py --provider vllm --model <served_alias> ...

Environment:
  VLLM_MODEL                   Required for start/serve if not already running.
  VLLM_ALIAS                   Served model name (default: local-vllm)
  VLLM_HOST                    Bind host for server (default: 0.0.0.0)
  VLLM_CLIENT_HOST             Host used for health checks/client base URL (default: 127.0.0.1)
  VLLM_PORT                    API port (default: 8000)
  VLLM_TP                      Tensor parallel size (default: 1)
  VLLM_DTYPE                   Model dtype (default: bfloat16)
  VLLM_GPU_MEMORY_UTILIZATION  GPU memory fraction (default: 0.9)
  VLLM_MAX_MODEL_LEN           Max model len (default: 8192)
  VLLM_MAX_NUM_BATCHED_TOKENS  Max batched tokens (default: 8192)
  VLLM_MAX_NUM_SEQS            Max concurrent sequences (default: 8)
  VLLM_ENFORCE_EAGER           Set 1 to pass --enforce-eager
  VLLM_KV_CACHE_DTYPE          Optional kv cache dtype (e.g. fp8)
  VLLM_ENABLE_AUTO_TOOL_CHOICE Set 1 to pass --enable-auto-tool-choice (default: 1)
  VLLM_TOOL_CALL_PARSER        Tool call parser name (default: gemma4)
  VLLM_HEALTH_TIMEOUT_SECONDS  Startup wait timeout (default: 300)
  VLLM_LOG_FILE                Server log path
  VLLM_PID_FILE                Server pid file path

Example:
  export VLLM_MODEL=/path/to/model
  ./evaluation_scripts/llm_eval/start_vllm.sh start
EOF
}

is_running() {
  if [[ ! -f "$PID_FILE" ]]; then
    return 1
  fi
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

health_ok() {
  # vLLM /health payload varies by version; HTTP 200 is enough.
  curl -fsS "$(health_url)" >/dev/null 2>&1
}

init_conda_shell() {
  # Non-interactive shells may expose only the conda binary (no shell function).
  if ! command -v conda >/dev/null 2>&1; then
    return 1
  fi
  eval "$(conda shell.bash hook)"
}

require_model() {
  if [[ -z "$VLLM_MODEL" ]]; then
    echo "ERROR: VLLM_MODEL is required." >&2
    echo "Set it to a local HF path or a model id before starting vLLM." >&2
    exit 1
  fi
}

build_server_cmd() {
  local extra=("$@")
  local cmd=(
    "$PYTHON_BIN" -m vllm.entrypoints.openai.api_server
    --model "$VLLM_MODEL"
    --served-model-name "$VLLM_ALIAS"
    --host "$VLLM_HOST"
    --port "$VLLM_PORT"
    --tensor-parallel-size "$VLLM_TP"
    --dtype "$VLLM_DTYPE"
    --gpu-memory-utilization "$VLLM_GPU_MEMORY_UTILIZATION"
    --max-model-len "$VLLM_MAX_MODEL_LEN"
    --max-num-batched-tokens "$VLLM_MAX_NUM_BATCHED_TOKENS"
    --max-num-seqs "$VLLM_MAX_NUM_SEQS"
  )

  if [[ "$VLLM_ENFORCE_EAGER" == "1" ]]; then
    cmd+=(--enforce-eager)
  fi
  if [[ -n "$VLLM_KV_CACHE_DTYPE" ]]; then
    cmd+=(--kv-cache-dtype "$VLLM_KV_CACHE_DTYPE")
  fi
  if [[ "$VLLM_ENABLE_AUTO_TOOL_CHOICE" == "1" ]]; then
    cmd+=(--enable-auto-tool-choice)
  fi
  if [[ -n "$VLLM_TOOL_CALL_PARSER" ]]; then
    cmd+=(--tool-call-parser "$VLLM_TOOL_CALL_PARSER")
  fi

  cmd+=("${extra[@]}")
  printf '%s\n' "${cmd[@]}"
}

start_server() {
  ### Purge current env and activate Triad env
  if init_conda_shell; then
    if [[ "${CONDA_SHLVL:-0}" -gt 0 ]]; then
      conda deactivate
    fi
  else
    echo "ERROR: conda is required to activate the Triad environment." >&2
    exit 1
  fi
  module --force purge
  conda activate Triad
  require_model

  if is_running; then
    echo "vLLM already running (pid=$(cat "$PID_FILE"))."
    return 0
  fi

  mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$PID_FILE")"
  local cmd_file
  cmd_file="$(mktemp)"
  build_server_cmd "$@" >"$cmd_file"
  mapfile -t cmd <"$cmd_file"
  rm -f "$cmd_file"

  nohup "${cmd[@]}" >>"$LOG_FILE" 2>&1 &
  local pid=$!
  echo "$pid" >"$PID_FILE"

  local timeout_s
  timeout_s="${VLLM_HEALTH_TIMEOUT_SECONDS}"
  local start_ts
  start_ts="$(date +%s)"

  until health_ok; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "ERROR: vLLM process exited during startup. See: $LOG_FILE" >&2
      tail -n 80 "$LOG_FILE" >&2 || true
      rm -f "$PID_FILE"
      exit 1
    fi

    local now elapsed
    now="$(date +%s)"
    elapsed=$((now - start_ts))
    if (( elapsed >= timeout_s )); then
      echo "ERROR: vLLM health check timed out after ${timeout_s}s. See: $LOG_FILE" >&2
      tail -n 80 "$LOG_FILE" >&2 || true
      kill "$pid" 2>/dev/null || true
      rm -f "$PID_FILE"
      exit 1
    fi
    sleep 1
  done

  echo "vLLM ready: alias=$VLLM_ALIAS base_url=$(api_base_url) pid=$pid"
}

serve_foreground() {
  require_model
  local cmd_file
  cmd_file="$(mktemp)"
  build_server_cmd "$@" >"$cmd_file"
  mapfile -t cmd <"$cmd_file"
  rm -f "$cmd_file"
  exec "${cmd[@]}"
}

stop_server() {
  if ! is_running; then
    echo "vLLM is not running."
    rm -f "$PID_FILE"
    return 0
  fi

  local pid
  pid="$(cat "$PID_FILE")"
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      echo "Stopped vLLM (pid=$pid)."
      return 0
    fi
    sleep 0.5
  done

  kill -9 "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "Force-stopped vLLM (pid=$pid)."
}

status_server() {
  if is_running; then
    local pid
    pid="$(cat "$PID_FILE")"
    if health_ok; then
      echo "vLLM running (pid=$pid) and healthy at $(api_base_url)"
    else
      echo "vLLM running (pid=$pid) but health endpoint not ready: $(health_url)"
    fi
    return 0
  fi

  echo "vLLM not running."
  return 1
}

main() {
  local command="${1:-}"
  shift || true

  case "$command" in
    start)
      start_server "$@"
      ;;
    serve)
      serve_foreground "$@"
      ;;
    stop)
      stop_server
      ;;
    status)
      status_server
      ;;
    logs)
      if [[ $# -eq 0 ]]; then
        tail -n 100 "$LOG_FILE"
      else
        tail "$@" "$LOG_FILE"
      fi
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      echo "ERROR: unknown command '$command'" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
