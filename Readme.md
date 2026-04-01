## First-Time Project Setup

Run this first:

```bash
conda create -n repo python=3.11
conda activate repo
pip install -r requirements.txt
```

## Evaluation Runners

This repo has two separate evaluation flows:

1. Cursor CLI in Docker (`run_cursor_eval_in_docker.sh`)
2. LLM + RepoMap host runner (`run_llm_repomap_eval_host.py`)

They are independent. `run_cursor_eval_in_docker.sh` does not run RepoMap.

## Cursor Evaluation (Docker)

Script: `run_cursor_eval_in_docker.sh`

### Auth details

- Cursor auth uses `CURSOR_API_KEY` only (or `--cursor-api-key`).

Get a Cursor key:
- https://cursor.com/dashboard/cloud-agents
- https://cursor.com/dashboard/cloud-agents#my-user-api-keys

Set it:

```bash
export CURSOR_API_KEY="your_cursor_key"
```

### Prerequisites

- Docker installed and running
- `jq` installed
- `cursor-agent` installed on host (the script copies it into each container)
- `Repositories.json` configured (repo -> image mapping)

### Usage

```bash
./run_cursor_eval_in_docker.sh --model <model_name> --repo <repo_name|all> [options]
```

Required:
- `--model` Cursor model name (example: `gpt-5.3-codex-high`)
- `--repo` one repo key in `Repositories.json`, or `all`

Optional:
- `--num-instances <n>` max instances per repo (default: `all`)
- `--cursor-api-key <key>` override `CURSOR_API_KEY`
- `--openai-api-key <key>` ignored by Cursor auth
- `--repos-file <path>` default `Repositories.json`
- `--instances-root <path>` default `qa_instances_eval`
- `--output-root <path>` default `evaluations/cursor`
- `--container-workdir <path>` default `/testbed`

### Output layout

- `evaluations/cursor/<model>/<repo>/<instance>/answer.json`
- `evaluations/cursor/<model>/<repo>/<instance>/cursor.log`

### Examples

```bash
./run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo Sympy
./run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo all --num-instances 10
./run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo Keras --cursor-api-key "$CURSOR_API_KEY"
```

## LLM + RepoMap Evaluation (Host-only, Read-only)

Script: `run_llm_repomap_eval_host.py`

This flow is host-side and read-only:
- Uses provider APIs (`openai`, `gemini`, `anthropic`)
- Uses read-only tools: `get_repo_map`, `list_dir`, `read_file`


### API keys

- OpenAI: `OPENAI_API_KEY`
- Gemini: `GOOGLE_API_KEY` or `GEMINI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`

Set keys in bash (set only what you need for your selected provider):

```bash
# OpenAI
export OPENAI_API_KEY="your_openai_key"

# Gemini (either variable works)
export GOOGLE_API_KEY="your_gemini_key"
# or
export GEMINI_API_KEY="your_gemini_key"

# Anthropic
export ANTHROPIC_API_KEY="your_anthropic_key"
```

### Usage

```bash
python3 run_llm_repomap_eval_host.py \
  --provider openai \
  --model gpt-5.4-2026-03-05 \
  --repo Sympy \
  --instances-root qa_instances_eval \
  --output-root evaluations
```

Model naming notes:
- For `--provider openai`, use OpenAI API model IDs (example: `gpt-5.3-codex`).
- Cursor aliases such as `gpt-5.3-codex-high` are not OpenAI API model IDs.

### Important options

- `--repo <name|all>` one repo under `qa_instances_eval`, or `all`
- `--num-instances <n|all>` default `all`
- `--repos-file <path>` default `Repositories.json` (used for snapshot materialization)
- `--mount-root <path>` default `.tmp_mounted_repos`
- `--materialize-missing-from-image` / `--no-materialize-missing-from-image`
- `--cleanup-mounted-repos` / `--no-cleanup-mounted-repos`
- `--repo-root <path>` single repo only
- `--repo-roots-file <json>`
- `--max-tool-rounds`, `--repomap-tokens`, `--max-read-lines`, `--max-read-chars`, `--max-repair-rounds`, `--temperature`
- `--print-llm-trace` / `--no-print-llm-trace`

### Output layout

- `evaluations/llm/<vendor>/<model>/<repo>/<instance>/answer.json`
- `evaluations/llm/<vendor>/<model>/<repo>/<instance>/llm.log`

## Scoring Against Oracle

Script: `evaluate_qa_answers.py`

```bash
python3 evaluate_qa_answers.py \
  --tool llm \
  --vendor openai \
  --model gpt-5.4-2026-03-05 \
  --repo Sympy \
  --qa-root qa_instances_eval \
  --eval-root evaluations
```

```bash
python3 evaluate_qa_answers.py \
  --tool cursor \
  --model gpt-5.3-codex-high \
  --repo Sympy \
  --qa-root qa_instances_eval \
  --eval-root evaluations
```

Oracle details:
- Oracle is read strictly from `qa_instances/<repo>/<instance>/oracle.json`.
- `--qa-root` is used to discover/select instances (typically `qa_instances_eval`).
