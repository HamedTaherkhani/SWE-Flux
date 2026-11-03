#!/usr/bin/env bash
# Leave-one-repo-out (LORO) evaluation driver.
#
# For each held-out repo R:
#   • point vLLM at the matching merged model:
#       <LORO_RUNS_ROOT>/loro-<R>-merged
#   • start vLLM via evaluation_scripts/llm_eval/start_vllm.sh
#   • run evaluation_scripts/llm_eval/run_llm_repomap_eval_host.py on repo R
#     (the held-out repo)
#   • write outputs under fine-tuning/evaluations/
#         fine-tuning/evaluations/llm/vllm/<ALIAS>/<R>/<instance>/answer.json
#   • stop vLLM before moving to the next fold
#
# Required env vars
#   LORO_RUNS_ROOT   Directory containing loro-<repo>-merged/ for every held-out
#                    repo. (i.e. the --output-root you passed to train_loro.py)
#
# Optional env vars
#   FOLDS            Space-separated list of held-out repos to evaluate.
#                    Default: every loro-*-merged dir under LORO_RUNS_ROOT.
#   ALIAS_PREFIX     Served-model alias prefix; default "gemma4-r64-loro".
#   EVAL_OUTPUT_ROOT Where eval traj/answer JSON go; default
#                    fine-tuning/evaluations.
#   CONTAINER_RUNTIME Snapshot materialization backend: apptainer, docker, or
#                    none. Default: none. Use none to git clone snapshots
#                    directly from RepoSnapshots.json instead of containers.
#   REPOBEHAVE_VLLM_MAX_TOKENS
#                    Per-request generation cap for vLLM chat calls. Default:
#                    1024 for this temporary LORO evaluation script. Set empty
#                    to remove the cap.
#   TRIAD_ENV        Conda env path used for host-side evaluation Python.
#                    Default: /project/def-hemmati-ac/hamedth/conda_envs/Triad_env.
#   Plus every VLLM_* var that start_vllm.sh honours.
#
# Example
#   LORO_RUNS_ROOT=/scratch/loro-runs \
#     fine-tuning/evaluate_loro.sh
#
#   # Re-run just one fold
#   LORO_RUNS_ROOT=/scratch/loro-runs FOLDS="Sympy" \
#     fine-tuning/evaluate_loro.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EVAL_DIR="$REPO_ROOT/evaluation_scripts/llm_eval"

LORO_RUNS_ROOT="${LORO_RUNS_ROOT:?Set LORO_RUNS_ROOT to the --output-root used in train_loro.py}"
if [[ ! -d "$LORO_RUNS_ROOT" ]]; then
  echo "ERROR: LORO_RUNS_ROOT does not exist: $LORO_RUNS_ROOT" >&2
  exit 1
fi

ALIAS_PREFIX="${ALIAS_PREFIX:-gemma4-r64-loro}"
EVAL_OUTPUT_ROOT="${EVAL_OUTPUT_ROOT:-$SCRIPT_DIR/evaluations}"
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-none}"
mkdir -p "$EVAL_OUTPUT_ROOT"

TRIAD_ENV="${TRIAD_ENV:-/project/def-hemmati-ac/hamedth/conda_envs/Triad_env}"
# These are gemma4 models trained with the reasoning dataset format (derivation
# + '## Answer' + JSON). Default to that protocol; override with ANSWER_FORMAT
# if you trained a bare-JSON adapter instead. (auto would also pick reasoning
# from the gemma4 alias, but be explicit here.)
ANSWER_FORMAT="${ANSWER_FORMAT:-reasoning}"

# vLLM server defaults — keep parity with run_vllm_eval.sh unless the user overrides.
export VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-30910}"
export VLLM_MAX_NUM_BATCHED_TOKENS="${VLLM_MAX_NUM_BATCHED_TOKENS:-30910}"
export VLLM_MAX_NUM_SEQS="${VLLM_MAX_NUM_SEQS:-1}"
export VLLM_KV_CACHE_DTYPE="${VLLM_KV_CACHE_DTYPE:-fp8}"
export VLLM_GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.9}"
export VLLM_ENFORCE_EAGER="${VLLM_ENFORCE_EAGER:-1}"
export VLLM_TP="${VLLM_TP:-1}"
export VLLM_ENABLE_AUTO_TOOL_CHOICE="${VLLM_ENABLE_AUTO_TOOL_CHOICE:-1}"
export VLLM_TOOL_CALL_PARSER="${VLLM_TOOL_CALL_PARSER:-gemma4}"
export VLLM_HEALTH_TIMEOUT_SECONDS="${VLLM_HEALTH_TIMEOUT_SECONDS:-2400}"
export VLLM_BASE_URL="${VLLM_BASE_URL:-http://${VLLM_CLIENT_HOST:-127.0.0.1}:${VLLM_PORT:-8000}/v1}"

# repomap config (mirrors run_vllm_eval.sh)
export REPOBEHAVE_REPOMAP_MAX_TOKENS="${REPOBEHAVE_REPOMAP_MAX_TOKENS:-10000}"
export REPOBEHAVE_REPOMAP_MAX_CHARS="${REPOBEHAVE_REPOMAP_MAX_CHARS:-50000}"
export REPOBEHAVE_TOOL_RESULT_JSON_MAX_CHARS="${REPOBEHAVE_TOOL_RESULT_JSON_MAX_CHARS:-60000}"
export REPOBEHAVE_CHEAP_REPOMAP_MAX_FILES="${REPOBEHAVE_CHEAP_REPOMAP_MAX_FILES:-2000}"
export CHEAP_REPOMAP_MAX_FILES="${CHEAP_REPOMAP_MAX_FILES:-$REPOBEHAVE_CHEAP_REPOMAP_MAX_FILES}"
if [[ -z "${REPOBEHAVE_VLLM_MAX_TOKENS+x}" ]]; then
  export REPOBEHAVE_VLLM_MAX_TOKENS="1024"
else
  export REPOBEHAVE_VLLM_MAX_TOKENS
fi

# Discover folds if not provided.
if [[ -z "${FOLDS:-}" ]]; then
  mapfile -t FOLD_LIST < <(
    find "$LORO_RUNS_ROOT" -maxdepth 1 -type d -name 'loro-*-merged' -printf '%f\n' \
      | sed -E 's/^loro-(.*)-merged$/\1/' \
      | sort
  )
else
  read -r -a FOLD_LIST <<< "$FOLDS"
fi

if [[ ${#FOLD_LIST[@]} -eq 0 ]]; then
  echo "ERROR: No folds found. Did training write loro-*-merged dirs under $LORO_RUNS_ROOT ?" >&2
  exit 1
fi

echo "Folds to evaluate: ${FOLD_LIST[*]}"
echo "Eval output root : $EVAL_OUTPUT_ROOT"
echo "vLLM max tokens  : ${REPOBEHAVE_VLLM_MAX_TOKENS:-uncapped}"
echo

# Make sure no stale vLLM is left running from a previous attempt.
"$EVAL_DIR/start_vllm.sh" stop || true

for repo in "${FOLD_LIST[@]}"; do
  MERGED_DIR="$LORO_RUNS_ROOT/loro-${repo}-merged"
  if [[ ! -d "$MERGED_DIR" ]]; then
    echo "[skip] no merged model for $repo at $MERGED_DIR" >&2
    continue
  fi

  ALIAS="${ALIAS_PREFIX}-${repo}"
  echo "============================================================"
  echo "FOLD: held-out=$repo"
  echo "  model dir : $MERGED_DIR"
  echo "  vLLM alias: $ALIAS"
  echo "============================================================"

  export VLLM_MODEL="$MERGED_DIR"
  export VLLM_ALIAS="$ALIAS"

# Start a fresh vLLM for this fold.
  "$EVAL_DIR/start_vllm.sh" start

  # The eval script expects an active conda env that matches the host (Triad).
  # Mirror run_vllm_eval.sh's env setup, but only if it isn't already activated.
  if command -v conda >/dev/null 2>&1; then
    eval "$(conda shell.bash hook)"
  fi
  if [[ "${CONDA_DEFAULT_ENV:-}" != "Triad" ]]; then
    [[ "${CONDA_SHLVL:-0}" -gt 0 ]] && conda deactivate || true
    module load StdEnv/2023 2>/dev/null || true
    if [[ "$CONTAINER_RUNTIME" == "apptainer" ]]; then
      module load apptainer/1.4.5 2>/dev/null || true
    fi
  fi

  if [[ "$CONTAINER_RUNTIME" == "apptainer" ]]; then
    # Keep Apptainer build/cache files in the user's home directory.
    export APPTAINER_TMPDIR="${APPTAINER_TMPDIR:-/home/hamedth/apptainer_tmp}"
    export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-/home/hamedth/apptainer_cache}"
    mkdir -p "$APPTAINER_TMPDIR" "$APPTAINER_CACHEDIR"
  fi
  export REPOBEHAVE_MOUNT_ROOT="${REPOBEHAVE_MOUNT_ROOT:-/home/hamedth/.tmp_mounted_repos}"
  mkdir -p "$REPOBEHAVE_MOUNT_ROOT"

  conda activate "$TRIAD_ENV"
  export PYTHON_BIN="$TRIAD_ENV/bin/python"

  echo "Eval Python: $("$PYTHON_BIN" -c 'import sys; print(sys.executable)')"
  if ! "$PYTHON_BIN" -c 'import openai' >/dev/null 2>&1; then
    echo "ERROR: eval Python cannot import openai: $PYTHON_BIN" >&2
    "$PYTHON_BIN" -c 'import sys; print(sys.executable); import openai'
    exit 1
  fi


  "${PYTHON_BIN:-python}" "$EVAL_DIR/run_llm_repomap_eval_host.py" \
    --provider vllm \
    --model "$ALIAS" \
    --answer-format "$ANSWER_FORMAT" \
    --repo "$repo" \
    --repo-map-mode none \
    --output-root "$EVAL_OUTPUT_ROOT" \
    --mount-root "$REPOBEHAVE_MOUNT_ROOT" \
    --container-runtime "$CONTAINER_RUNTIME" \
    --refresh-mounted-repos

  "$EVAL_DIR/start_vllm.sh" stop
  echo
done

echo "Done. Evaluation outputs are under: $EVAL_OUTPUT_ROOT"
echo "Structure:  <output-root>/llm/vllm/<alias>/<repo>/<instance>/{answer,traj}.json"
