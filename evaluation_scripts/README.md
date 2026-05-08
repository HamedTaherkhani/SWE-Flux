
# Prerequisites

- Docker installed and running
- `jq` installed

## Evaluation Scripts

All evaluation runners and evaluation helper scripts are documented here.

Runner order in this doc:
1. LLM
2. Cursor CLI
3. Claude Code CLI
4. SWE-Agent / mini-SWE-Agent

# 1- LLM + RepoMap Evaluation

Script: `evaluation_scripts/run_llm_repomap_eval_host.py`

This flow is host-side and read-only:
- Uses provider APIs (`openai`, `gemini`, `anthropic`, `fireworks`, `openrouter`, `vllm`)
- Uses read-only tools: `get_repo_map`, `list_dir`, `read_file`

## For evaluation using local llm (vllm), you need to activate Triad_env (root `environment.yml`, conda env name `Triad_env` — see the project `Readme.md`):

```bash
conda activate Triad_env
```
## For evaluation using other providers (including openai, gemeini, anthropic, fireworks, and openrouter) activate repo:
```bash
conda activate repo
```

### API keys

- OpenAI: `OPENAI_API_KEY`
- Gemini: `GOOGLE_API_KEY` or `GEMINI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- OpenRouter: `OPENROUTER_API_KEY`
- vLLM: `VLLM_BASE_URL` (default `http://127.0.0.1:8000/v1`) and optional `VLLM_API_KEY`

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

# OpenRouter
export OPENROUTER_API_KEY="your_openrouter_key"

# vLLM (local OpenAI-compatible endpoint)
export VLLM_BASE_URL="http://127.0.0.1:8000/v1"
export VLLM_API_KEY="EMPTY"
```

### Usage

```bash
python3 evaluation_scripts/llm_eval/run_llm_repomap_eval_host.py \
  --provider openai \
  --model gpt-5.4-2026-03-05 \
  --repo Sympy \
  --instances-root qa_instances_eval \
  --output-root evaluations

python3 evaluation_scripts/llm_eval/run_llm_repomap_eval_host.py \
  --provider openai \
  --model gpt-5.4-2026-03-05 \
  --repo all \
  --resume \
  --instances-root qa_instances_eval \
  --output-root evaluations

python3 evaluation_scripts/llm_eval/run_llm_repomap_eval_host.py \
  --provider vllm \
  --model local-vllm \
  --repo Sympy \
  --instances-root qa_instances_eval \
  --output-root evaluations
```

Model naming notes:
- For `--provider openai`, use OpenAI API model IDs (example: `gpt-5.3-codex`).
- For `--provider openrouter`, use OpenRouter model IDs (example: `google/gemma-4-31b-it`).
- For `--provider vllm`, use the served model alias from your local vLLM server (example: `local-vllm`).
- Cursor aliases such as `gpt-5.3-codex-high` are not OpenAI API model IDs.

For a managed local vLLM lifecycle, use:
- `evaluation_scripts/llm_eval/start_vllm.sh`

### Important options

- `--repo <name|all>` one repo under `qa_instances_eval`, or `all`
- `--num-instances <n|all>` default `all`
- `--resume` skip instances that already have a non-empty `answer.json`
- `--repos-file <path>` default `Repositories.json` (used for snapshot materialization)
- `--mount-root <path>` default `.tmp_mounted_repos`
- `--materialize-missing-from-image` / `--no-materialize-missing-from-image`
- `--cleanup-mounted-repos` / `--no-cleanup-mounted-repos`
- `--repo-root <path>` single repo only
- `--repo-roots-file <json>`
- `--max-read-lines`, `--max-read-chars`, `--max-repair-rounds`, `--temperature`
- `--print-llm-trace` / `--no-print-llm-trace`

### Output layout

- `evaluations/llm/<vendor>/<model>/<repo>/<instance>/answer.json`
- `evaluations/llm/<vendor>/<model>/<repo>/<instance>/llm.log`

# 2- Cursor Evaluation

Script: `evaluation_scripts/run_cursor_eval_in_docker.sh`

### Auth details

- Cursor auth uses `CURSOR_API_KEY` only (or `--cursor-api-key`).

Get a Cursor key:
- https://cursor.com/dashboard/cloud-agents
- https://cursor.com/dashboard/cloud-agents#my-user-api-keys

Set it:

```bash
export CURSOR_API_KEY="your_cursor_key"
```

### Prerequisity

- `cursor-agent` installed on host (the script copies it into each container. Install from https://cursor.com/docs/cli/installation)

### Usage

```bash
./evaluation_scripts/run_cursor_eval_in_docker.sh --model <model_name> --repo <repo_name|all> [options]
```

Required:
- `--model` Cursor model name (example: `gpt-5.3-codex-high`)
- `--repo` one repo key in `Repositories.json`, or `all`

Optional:
- `--num-instances <n>` max instances per repo (default: `all`)
- `--resume` skip instances that already have a non-empty `answer.json`
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
./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo Sympy --cursor-api-key "$CURSOR_API_KEY"
./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo all --num-instances 10 --cursor-api-key "$CURSOR_API_KEY"
./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo Keras --cursor-api-key "$CURSOR_API_KEY"
./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo all --resume --cursor-api-key "$CURSOR_API_KEY"
```

### Find available models

Install Cursor CLI agent on macOS/Linux:

```bash
curl https://cursor.com/install -fsS | bash
```

Login Cursor CLI agent:

```bash
agent login
```

List models:

```bash
agent models
```

# 3- Claude Code Evaluation

Script: `evaluation_scripts/run_claude_code_eval_in_docker.sh`

### Auth details

- Claude Code auth in this runner uses `ANTHROPIC_API_KEY` (or `--anthropic-api-key`).

Get an Anthropic API key:
- https://console.anthropic.com/settings/keys
- Click **Create Key** and copy the key value.

Set it:

```bash
export ANTHROPIC_API_KEY="your_anthropic_key"
```

### Usage

```bash
./evaluation_scripts/run_claude_code_eval_in_docker.sh --model <model_name> --repo <repo_name|all> [options]
```

Required:
- `--model` Claude model name (example: `claude-sonnet-4-6`)
- `--repo` one repo key in `Repositories.json`, or `all`

Optional:
- `--num-instances <n>` max instances per repo (default: `all`)
- `--resume` skip instances that already have a non-empty `answer.json`
- `--anthropic-api-key <key>` override `ANTHROPIC_API_KEY`
- `--claude-extra-args "<args>"` extra args passed to Claude CLI
- `--no-auto-install` disable automatic Claude CLI install in container
- `--repos-file <path>` default `Repositories.json`
- `--instances-root <path>` default `qa_instances_eval`
- `--output-root <path>` default `evaluations/claude_code`
- `--container-workdir <path>` default `/testbed`

### Output layout

- `evaluations/claude_code/<model>/<repo>/<instance>/answer.json`
- `evaluations/claude_code/<model>/<repo>/<instance>/traj.json`
- `evaluations/claude_code/<model>/<repo>/<instance>/claude.log`

### Examples

```bash
./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo Sympy --anthropic-api-key "$ANTHROPIC_API_KEY"
./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo all --anthropic-api-key "$ANTHROPIC_API_KEY"
./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo Keras --num-instances 10 --anthropic-api-key "$ANTHROPIC_API_KEY"
./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo all --resume --anthropic-api-key "$ANTHROPIC_API_KEY"
```

### Find available models

Replace `$ANTHROPIC_API_KEY` with your actual key:

```bash
curl https://api.anthropic.com/v1/models \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
| jq -r '.data[] | "\(.id)\t\(.display_name)"'
```

# 4- SWE-Agent / mini-SWE-Agent Evaluation

Script: `evaluation_scripts/run_swe_agent_eval_in_docker.sh`

This flow runs either SWE-Agent or mini-SWE-Agent inside each benchmark container.

### API keys

Set only the key(s) needed by your selected model/provider:

- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- Gemini: `GOOGLE_API_KEY` or `GEMINI_API_KEY`
- OpenRouter: `OPENROUTER_API_KEY`

Example:

```bash
export OPENAI_API_KEY="your_openai_key"
# or:
export ANTHROPIC_API_KEY="your_anthropic_key"
export GEMINI_API_KEY="your_gemini_key"
export OPENROUTER_API_KEY="your_openrouter_key"
```

### Usage

```bash
./evaluation_scripts/run_swe_agent_eval_in_docker.sh \
  --agent <swe-agent|mini-swe-agent> \
  --model <model_name> \
  --repo <repo_name|all> \
  [options]
```

Required:
- `--agent` choose `swe-agent` or `mini-swe-agent`
- `--model` model name for the selected agent (example: `openai/gpt-5.4`)
- `--repo` one repo key in `Repositories.json`, or `all`

Optional:
- `--num-instances <n>` max instances per repo (default: `all`)
- `--resume` skip instances that already have a non-empty `answer.json`
- `--agent-extra-args "<args>"` extra args forwarded to selected agent CLI
- `--repos-file <path>` default `Repositories.json`
- `--instances-root <path>` default `qa_instances_eval`
- `--output-root <path>` default `evaluations`
- `--container-workdir <path>` default `/testbed`
- `--openai-api-key <key>`, `--anthropic-api-key <key>`, `--google-api-key <key>`, `--gemini-api-key <key>`, `--openrouter-api-key <key>`
- `--no-auto-install` disable automatic agent installation in container

### Output layout

- `evaluations/swe-agent/<model>/<repo>/<instance>/answer.json`
- `evaluations/swe-agent/<model>/<repo>/<instance>/sweagent.log`
- `evaluations/mini-swe-agent/<model>/<repo>/<instance>/answer.json`
- `evaluations/mini-swe-agent/<model>/<repo>/<instance>/mini.log`

### Examples

```bash
./evaluation_scripts/run_swe_agent_eval_in_docker.sh --agent mini-swe-agent --model openai/gpt-5.4 --repo Sympy
./evaluation_scripts/run_swe_agent_eval_in_docker.sh --agent swe-agent --model openai/gpt-5.4 --repo all --num-instances 10
./evaluation_scripts/run_swe_agent_eval_in_docker.sh --agent mini-swe-agent --model openai/gpt-5.4 --repo Keras --openai-api-key "$OPENAI_API_KEY"
./evaluation_scripts/run_swe_agent_eval_in_docker.sh --agent mini-swe-agent --model openai/gpt-5.4 --repo all --resume
```

# Scoring Against Oracle

Script: `evaluation_scripts/evaluate_qa_answers.py`

```bash
python3 evaluation_scripts/evaluate_qa_answers.py \
  --tool llm \
  --vendor openai \
  --model gpt-5.4-2026-03-05 \
  --repo Sympy \
  --qa-root qa_instances_eval \
  --eval-root evaluations
```

```bash
python3 evaluation_scripts/evaluate_qa_answers.py \
  --tool llm \
  --vendor vllm \
  --model local-vllm \
  --repo Sympy \
  --qa-root qa_instances_eval \
  --eval-root evaluations
```

```bash
python3 evaluation_scripts/evaluate_qa_answers.py \
  --tool cursor \
  --model gpt-5.3-codex-high \
  --repo Sympy \
  --qa-root qa_instances_eval \
  --eval-root evaluations
```

```bash
python3 evaluation_scripts/evaluate_qa_answers.py \
  --tool claude_code \
  --model claude-sonnet-4-6 \
  --repo Sympy \
  --qa-root qa_instances_eval \
  --eval-root evaluations
```

```bash
python3 evaluation_scripts/evaluate_qa_answers.py \
  --tool swe-agent \
  --model openai_gpt-5.4 \
  --repo Sympy \
  --qa-root qa_instances_eval \
  --eval-root evaluations
```

```bash
python3 evaluation_scripts/evaluate_qa_answers.py \
  --tool mini-swe-agent \
  --model openai_gpt-5.4 \
  --repo Sympy \
  --qa-root qa_instances_eval \
  --eval-root evaluations
```

Oracle details:
- Oracle is read from `qa_instances/<repo>/<instance>/oracle.json`.
- `--qa-root` is used to discover/select instances (typically `qa_instances_eval`).
