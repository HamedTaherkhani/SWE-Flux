
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
- `--output-root <path>` default `evaluations/cursor` (or `evaluations/cursor-noexec` with `--no-exec`)
- `--container-workdir <path>` default `/testbed`
- `--no-exec` static mode: the agent can read the repo but cannot execute anything (see below)
- `--sandbox-image <image>` base image for the `--no-exec` sandbox (default `ubuntu:22.04`)

### Static mode (`--no-exec`)

Use this to evaluate Cursor with repository access but **no access to the running environment**
(no tests, no Python, no shell). Two independent guards enforce it:

1. **No environment.** The repo (plus `qa_instances_eval/<repo>`) is snapshotted out of the
   repository's Docker image and mounted **read-only** into a minimal sandbox container
   (`ubuntu:22.04` by default) that has no Python, pytest, or project dependencies. Only the
   per-repo output directory is writable. The script refuses to start if the sandbox image
   contains `python`/`pytest`.
2. **Shell tool denied.** A Cursor CLI permissions file (`~/.cursor/cli-config.json`) with
   `"deny": ["Shell(*)"]` is written in the sandbox, so every shell tool call is rejected with
   `Command blocked by permissions configuration`. `--force` honours explicit deny rules.

The prompt is also switched to a static-reasoning variant that tells the agent execution is
unavailable and to derive the answer by reading code and tests. Results land under
`evaluations/cursor-noexec/<model>/...` so they never mix with full-access runs, and
`evaluate_qa_answers.py --tool cursor-noexec --model <model>` scores them.

### Output layout

- `evaluations/cursor/<model>/<repo>/<instance>/answer.json`
- `evaluations/cursor/<model>/<repo>/<instance>/cursor.log`
- `evaluations/cursor/<model>/<repo>/<instance>/traj.json`
- With `--no-exec`: same layout under `evaluations/cursor-noexec/`

### Examples

```bash
./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo Sympy --cursor-api-key "$CURSOR_API_KEY"
./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo all --num-instances 10 --cursor-api-key "$CURSOR_API_KEY"
./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo Keras --cursor-api-key "$CURSOR_API_KEY"
./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo all --resume --cursor-api-key "$CURSOR_API_KEY"
# Static mode: repo readable, nothing executable
./evaluation_scripts/run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo Sympy --no-exec --cursor-api-key "$CURSOR_API_KEY"
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

# 2b- Codex Evaluation

Script: `evaluation_scripts/run_codex_eval_in_docker.sh`

Runs OpenAI Codex CLI (`codex exec --json`) on the QA instances. The Codex binary is copied from
the host into each container (it is a static binary, so it runs in both the repository images
and the minimal `--no-exec` sandbox).

### Prerequisites

- A Codex CLI binary on the host: `codex` on `PATH`, or the one bundled with the Cursor/ChatGPT
  extension (`~/.cursor/extensions/openai.chatgpt-*/bin/linux-x86_64/codex`, auto-detected),
  or pass `--codex-bin <path>`.
- Authentication, one of:
  - `--openai-api-key <key>` (or `OPENAI_API_KEY` / `openai_api_key` env): API-key billing.
  - `~/.codex/auth.json` from a `codex login` on the host (ChatGPT plan), or `--codex-auth-file <path>`.
    Used automatically when no API key is given.

### Usage

```bash
./evaluation_scripts/run_codex_eval_in_docker.sh --model <model_name> --repo <repo_name|all> [options]
```

Required:
- `--model` Codex model name (example: `gpt-5.4`, `gpt-5.3-codex`)
- `--repo` one repo key in `Repositories.json`, or `all`

Optional:
- `--num-instances <n>` max instances per repo (default: `all`)
- `--reasoning-effort <low|medium|high|xhigh>` sets `model_reasoning_effort`; appended to the output model dir name
- `--resume` skip instances that already have a non-empty `answer.json`
- `--timeout <seconds>` per-instance timeout (default `600`)
- `--output-root <path>` default `evaluations/codex` (or `evaluations/codex-noexec` with `--no-exec`)
- `--no-exec` static mode (see below)
- `--sandbox-image <image>` base image for the `--no-exec` sandbox (default `ubuntu:22.04`)
- `--repos-file`, `--instances-root`, `--container-workdir` as for the Cursor runner

Codex runs with `--dangerously-bypass-approvals-and-sandbox` because the Docker container is
the sandbox; `web_search` is disabled in the generated config so the agent can only use the repo.

### Static mode (`--no-exec`)

Same design as the Cursor static mode: the repo (plus `qa_instances_eval/<repo>`) is snapshotted
out of the repository image and mounted **read-only** into a minimal `ubuntu:22.04` sandbox that
has no Python, pytest, or project dependencies; only the per-repo output directory is writable,
and the script refuses to start if the sandbox image contains `python`/`pytest`.

One difference from Cursor: Codex has no separate file-reading tool, it reads files through the
shell (`cat`, `sed -n`, `rg`). The shell therefore stays available, but nothing in the sandbox
can execute the project. The prompt tells the agent this and asks it to reason statically.

### Output layout

- `evaluations/codex/<model>/<repo>/<instance>/answer.json`
- `evaluations/codex/<model>/<repo>/<instance>/traj.json` (Codex `--json` events: `command_execution`, `file_change`, `agent_message`, `turn.completed` usage)
- `evaluations/codex/<model>/<repo>/<instance>/codex.log`
- `evaluations/codex/<model>/<repo>/<instance>/last_message.txt`
- With `--no-exec`: same layout under `evaluations/codex-noexec/`

Score with `evaluate_qa_answers.py --tool codex --model <model>` (or `--tool codex-noexec`).

### Examples

```bash
./evaluation_scripts/run_codex_eval_in_docker.sh --model gpt-5.4 --repo Sympy
./evaluation_scripts/run_codex_eval_in_docker.sh --model gpt-5.4 --reasoning-effort high --repo all --num-instances 10
# Static mode: repo readable, nothing executable
./evaluation_scripts/run_codex_eval_in_docker.sh --model gpt-5.4 --repo all --no-exec --resume
```

# 3- Claude Code Evaluation

Script: `evaluation_scripts/run_claude_code_eval_in_docker.sh`

### Auth details

- Claude Code auth in this runner uses `ANTHROPIC_API_KEY` (or `--anthropic-api-key`).
- If no API key is given, the host's Claude subscription login is used instead: the OAuth
  credentials file (`~/.claude/.credentials.json`, from `claude login` on the host, or
  `--claude-credentials <path>`) is copied into the container.

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
- `--output-root <path>` default `evaluations/claude_code` (or `evaluations/claude_code-noexec` with `--no-exec`)
- `--container-workdir <path>` default `/testbed`
- `--parallel <n>` run up to n instances concurrently per repo (default `1`)
- `--effort <low|medium|high|xhigh|max>` Claude Code effort level; appended to the output model dir name (default: CLI built-in)
- `--claude-credentials <path>` OAuth credentials file used when no API key is given
- `--no-exec` static mode (see below)
- `--sandbox-image <image>` base image for the `--no-exec` sandbox (default `ubuntu:22.04`)
- `--claude-bin <path>` host native `claude` binary copied into the `--no-exec` sandbox (default: resolved from `PATH`)

### Static mode (`--no-exec`)

Same design as the Cursor and Codex static modes: the repo (plus `qa_instances_eval/<repo>`) is
snapshotted out of the repository image and mounted **read-only** into a minimal `ubuntu:22.04`
sandbox with no Python, pytest, or project dependencies; only the per-repo output directory is
writable, and the script refuses to start if the sandbox image contains `python`/`pytest`. The
host's native `claude` binary is copied in, so no installer runs in the sandbox.

Claude Code has separate file tools, so execution is also removed at the tool level: the session
is started with `--tools "Read,Glob,Grep,Write,Edit"` and
`--disallowedTools "Bash,WebFetch,WebSearch,Task,Agent,NotebookEdit"`. The `system/init` event in
`traj.json` lists the tools the session actually had, which makes this auditable per instance.

The prompt is switched to a static-reasoning variant. Results land under
`evaluations/claude_code-noexec/<model>/...`; score with
`evaluate_qa_answers.py --tool claude_code-noexec --model <model>`.

### Output layout

- `evaluations/claude_code/<model>/<repo>/<instance>/answer.json`
- `evaluations/claude_code/<model>/<repo>/<instance>/traj.json`
- `evaluations/claude_code/<model>/<repo>/<instance>/claude.log`
- With `--no-exec`: same layout under `evaluations/claude_code-noexec/`

### Examples

```bash
./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo Sympy --anthropic-api-key "$ANTHROPIC_API_KEY"
./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo all --anthropic-api-key "$ANTHROPIC_API_KEY"
./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo Keras --num-instances 10 --anthropic-api-key "$ANTHROPIC_API_KEY"
./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo all --resume --anthropic-api-key "$ANTHROPIC_API_KEY"
# Static mode with the host's subscription login, 4 instances at a time
./evaluation_scripts/run_claude_code_eval_in_docker.sh --model claude-sonnet-4-6 --repo Sympy --no-exec --parallel 4
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
