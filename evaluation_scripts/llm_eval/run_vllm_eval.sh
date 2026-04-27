#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_REPO="${1:-}"

# Use active env Python by default. Override with PYTHON_BIN if needed.
export PYTHON_BIN="${PYTHON_BIN:-python}"

# 1) Start server
# DEFAULT_VLLM_MODEL="/home/hamedth/projects/def-hemmati-ac/hamedth/hugging_face/gemma4-31b"
DEFAULT_VLLM_MODEL="/home/hamedth/projects/def-hemmati-ac/hamedth/hugging_face/gemma4-4b"
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
export VLLM_TP="${VLLM_TP:-1}"
export VLLM_ENABLE_AUTO_TOOL_CHOICE="${VLLM_ENABLE_AUTO_TOOL_CHOICE:-1}"
export VLLM_TOOL_CALL_PARSER="${VLLM_TOOL_CALL_PARSER:-gemma4}"




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
conda activate Triad

if [[ -n "$TARGET_REPO" ]]; then
  REPOS=("$TARGET_REPO")
else
  mapfile -t REPOS < <(
    "$PYTHON_BIN" -c '
import json
from pathlib import Path

repos = json.loads(Path("'"$REPO_ROOT"'/Repositories.json").read_text())
for repo_name in repos:
    if repo_name not in {"Sympy", "yt_dlp"}:
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
    --container-runtime apptainer \
    --refresh-mounted-repos
done

# 4) Stop server when done
# "$SCRIPT_DIR/start_vllm.sh" stop
