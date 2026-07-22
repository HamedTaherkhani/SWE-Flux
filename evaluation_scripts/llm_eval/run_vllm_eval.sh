#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_REPO="${1:-}"
TRIAD_ENV="/project/def-hemmati-ac/hamedth/conda_envs/Triad_env"

# 1) Start server
DEFAULT_VLLM_MODEL="/home/hamedth/projects/def-hemmati-ac/hamedth/hugging_face/gemma4-31b"
# DEFAULT_VLLM_MODEL="/home/hamedth/projects/def-hemmati-ac/hamedth/hugging_face/gemma4-4b"
export VLLM_MODEL="${VLLM_MODEL:-$DEFAULT_VLLM_MODEL}"

# Keep served name aligned with the selected model path unless explicitly overridden.
export VLLM_ALIAS="${VLLM_ALIAS:-$(basename "$VLLM_MODEL")}"
# export VLLM_ALIAS="${VLLM_ALIAS:-$(basename "$VLLM_MODEL")}_run_2"

export VLLM_HEALTH_TIMEOUT_SECONDS="${VLLM_HEALTH_TIMEOUT_SECONDS:-2400}"
echo "VLLM_ALIAS: $VLLM_ALIAS"

# Stable high-context settings for 80GB single GPU.
export VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-30910}"
export VLLM_MAX_NUM_BATCHED_TOKENS="${VLLM_MAX_NUM_BATCHED_TOKENS:-30910}"
export VLLM_MAX_NUM_SEQS="${VLLM_MAX_NUM_SEQS:-1}"
export VLLM_KV_CACHE_DTYPE="${VLLM_KV_CACHE_DTYPE:-fp8}"
export VLLM_GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.9}"
export VLLM_ENFORCE_EAGER="${VLLM_ENFORCE_EAGER:-1}"
export VLLM_TP="${VLLM_TP:-2}"
export VLLM_ENABLE_AUTO_TOOL_CHOICE="${VLLM_ENABLE_AUTO_TOOL_CHOICE:-1}"
export VLLM_TOOL_CALL_PARSER="${VLLM_TOOL_CALL_PARSER:-gemma4}"
export VLLM_BASE_URL="${VLLM_BASE_URL:-http://${VLLM_CLIENT_HOST:-127.0.0.1}:${VLLM_PORT:-8000}/v1}"




## repomap config
export REPOBEHAVE_REPOMAP_MAX_TOKENS="${REPOBEHAVE_REPOMAP_MAX_TOKENS:-10000}"
export REPOBEHAVE_REPOMAP_MAX_CHARS="${REPOBEHAVE_REPOMAP_MAX_CHARS:-50000}"
export REPOBEHAVE_TOOL_RESULT_JSON_MAX_CHARS="${REPOBEHAVE_TOOL_RESULT_JSON_MAX_CHARS:-60000}"
export REPOBEHAVE_CHEAP_REPOMAP_MAX_FILES="${REPOBEHAVE_CHEAP_REPOMAP_MAX_FILES:-2000}"
export CHEAP_REPOMAP_MAX_FILES="${CHEAP_REPOMAP_MAX_FILES:-$REPOBEHAVE_CHEAP_REPOMAP_MAX_FILES}"



# "$SCRIPT_DIR/start_vllm.sh" start

# 2) (Optional) verify
"$SCRIPT_DIR/start_vllm.sh" status

# Initialize conda for non-interactive shells so activate/deactivate work.
if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
fi

if [[ "${CONDA_SHLVL:-0}" -gt 0 ]]; then
  conda deactivate
fi

module load StdEnv/2023
module load apptainer/1.4.5

# Keep Apptainer build/cache files in the user's home directory.
export APPTAINER_TMPDIR="${APPTAINER_TMPDIR:-/home/hamedth/apptainer_tmp}"
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-/home/hamedth/apptainer_cache}"
export REPOBEHAVE_MOUNT_ROOT="${REPOBEHAVE_MOUNT_ROOT:-/home/hamedth/.tmp_mounted_repos}"
mkdir -p "$APPTAINER_TMPDIR" "$APPTAINER_CACHEDIR" "$REPOBEHAVE_MOUNT_ROOT"

conda activate "$TRIAD_ENV"
export PYTHON_BIN="$TRIAD_ENV/bin/python"

echo "Eval Python: $("$PYTHON_BIN" -c 'import sys; print(sys.executable)')"
if ! "$PYTHON_BIN" -c 'import openai' >/dev/null 2>&1; then
  echo "ERROR: eval Python cannot import openai: $PYTHON_BIN" >&2
  "$PYTHON_BIN" -c 'import sys; print(sys.executable); import openai'
  exit 1
fi

if [[ -n "$TARGET_REPO" ]]; then
  REPOS=("$TARGET_REPO")
else
  mapfile -t REPOS < <(
    "$PYTHON_BIN" -c '
import json
from pathlib import Path

repos = json.loads(Path("'"$REPO_ROOT"'/Repositories.json").read_text())
for repo_name in repos:
    print(repo_name)
'
  )
fi

for repo in "${REPOS[@]}"; do
  echo "Running LLM repomap eval for repo: $repo"
  "$PYTHON_BIN" "$REPO_ROOT/evaluation_scripts/llm_eval/run_llm_repomap_eval_host.py" \
    --provider vllm \
    --model "$VLLM_ALIAS" \
    --repo-map-mode none \
    --repo "$repo" \
    --container-runtime none \
    --mount-root "$REPOBEHAVE_MOUNT_ROOT" \
    --refresh-mounted-repos \
    --resume
done

# 4) Stop server when done
# "$SCRIPT_DIR/start_vllm.sh" stop
