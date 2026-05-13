#!/usr/bin/env bash
# Score LORO evaluation outputs against oracles.
#
# Walks fine-tuning/evaluations/llm/vllm/gemma4-r64-loro-<repo>/ and runs
# evaluation_scripts/evaluate_qa_answers.py for each fold, then prints a
# rolled-up table. Each fold's alias only contains predictions for its
# held-out repo (the rest weren't evaluated for that model).
#
# Optional env vars
#   EVAL_OUTPUT_ROOT  Where evaluate_loro.sh wrote its outputs.
#                     Default: fine-tuning/evaluations
#   ALIAS_PREFIX      Prefix that identifies LORO folds. Default: gemma4-r64-loro
#   FOLDS             Space-separated repo subset. Default: every alias found.
#   EXCEL             Path to also write an Excel report. Optional.
#
# Example
#   ./fine-tuning/score_loro.sh
#   EXCEL=loro_results.xlsx ./fine-tuning/score_loro.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

EVAL_OUTPUT_ROOT="${EVAL_OUTPUT_ROOT:-$SCRIPT_DIR/evaluations}"
ALIAS_PREFIX="${ALIAS_PREFIX:-gemma4-r64-loro}"
SCORER="$REPO_ROOT/evaluation_scripts/evaluate_qa_answers.py"

if [[ ! -d "$EVAL_OUTPUT_ROOT/llm/vllm" ]]; then
  echo "ERROR: no vLLM eval outputs under $EVAL_OUTPUT_ROOT/llm/vllm" >&2
  echo "       did you run evaluate_loro.sh first?" >&2
  exit 1
fi

# Discover aliases (one per fold) unless caller restricted via FOLDS.
declare -a FOLD_LIST
if [[ -z "${FOLDS:-}" ]]; then
  mapfile -t FOLD_LIST < <(
    find "$EVAL_OUTPUT_ROOT/llm/vllm" -maxdepth 1 -mindepth 1 -type d -name "${ALIAS_PREFIX}-*" \
      -printf '%f\n' \
      | sed -E "s/^${ALIAS_PREFIX}-//" \
      | sort
  )
else
  read -r -a FOLD_LIST <<< "$FOLDS"
fi

if [[ ${#FOLD_LIST[@]} -eq 0 ]]; then
  echo "ERROR: no folds matched alias prefix '${ALIAS_PREFIX}-*' under $EVAL_OUTPUT_ROOT/llm/vllm" >&2
  exit 1
fi

echo "Scorer       : $SCORER"
echo "Eval root    : $EVAL_OUTPUT_ROOT"
echo "Alias prefix : $ALIAS_PREFIX"
echo "Folds        : ${FOLD_LIST[*]}"
echo

for repo in "${FOLD_LIST[@]}"; do
  alias="${ALIAS_PREFIX}-${repo}"
  echo "============================================================"
  echo "FOLD: held-out=$repo  alias=$alias"
  echo "============================================================"
  "${PYTHON_BIN:-python}" "$SCORER" \
    --tool llm \
    --vendor vllm \
    --model "$alias" \
    --repo "$repo" \
    --eval-root "$EVAL_OUTPUT_ROOT"
  echo
done

# Aggregate run — discover-all over the same eval root.
echo "============================================================"
echo "AGGREGATE across all folds"
echo "============================================================"
extra=()
if [[ -n "${EXCEL:-}" ]]; then
  extra+=(--excel "$EXCEL")
fi
"${PYTHON_BIN:-python}" "$SCORER" --all --eval-root "$EVAL_OUTPUT_ROOT" "${extra[@]}"
