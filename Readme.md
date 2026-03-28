## Run Evaluation With Cursor CLI

### 1) Get a Cursor API key

- Open Cursor Cloud Agents dashboard: https://cursor.com/dashboard/cloud-agents
- API keys section: https://cursor.com/dashboard/cloud-agents#my-user-api-keys
- Create a new user API key there.
- Export it in your shell:

```bash
export CURSOR_API_KEY="your_key_here"
```

You can also pass it directly with `--cursor-api-key` in the docker runner.

### 2) Prerequisites

- Docker installed and running
- `jq` installed
- `cursor-agent` installed on host (the docker runner copies it into the container)
- Repo/image mapping configured in `Repositories.json`

### 3) Docker Evaluation Runner (recommended)

Script: `run_cursor_eval_in_docker.sh`

```bash
./run_cursor_eval_in_docker.sh --model <model_name> --repo <repo_name|all> [options]
```

Required arguments:

- `--model`: Cursor model name (example: `gpt-5.3-codex-high`)
- `--repo`: one repo key from `Repositories.json` (`Sympy`, `Keras`, `Telegram_bot`, etc.) or `all`

Optional arguments:

- `--num-instances <n>`: max instances per repo (default: `all`)
- `--cursor-api-key <key>`: API key override (default reads `CURSOR_API_KEY`)
- `--repos-file <path>`: repo/image JSON (default: `Repositories.json`)
- `--instances-root <path>`: root containing `qa_instances_eval/<repo>` (default: `qa_instances_eval`)
- `--output-root <path>`: output root (default: `evaluations/cursor`)
- `--container-workdir <path>`: project dir in container (default: `/testbed`)

What it does:

- Pulls image if missing
- Starts container for each repo
- Copies `qa_instances_eval/<repo>` into `/testbed/qa_instances_eval/<repo>`
- Runs Cursor per instance with `--force` and separate prompt/session
- Copies outputs back to:
  - `evaluations/cursor/<model>/<repo>/<instance>/answer.json`
  - `evaluations/cursor/<model>/<repo>/<instance>/cursor.log`

Examples:

```bash
./run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo Sympy
./run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo all --num-instances 10
./run_cursor_eval_in_docker.sh --model gpt-5.3-codex-high --repo Keras --cursor-api-key "$CURSOR_API_KEY"
```