## Project Setup

## Setup these 2 environments separately for evaluation:

### 1
```bash
conda create -n repo python=3.11
conda activate repo
pip install -r requirements.txt
conda deactivate
```

### 2

```bash
conda env create -f environment.yml
```

## Evaluation Scripts

All evaluation runner and scoring docs were moved to:
- [evaluation_scripts/README.md](evaluation_scripts/README.md)

Start there for:
- LLM evaluation
- Cursor/Claude/SWE-Agent evaluations
- Scoring with `evaluate_qa_answers.py`


## Oracle Autoharvesting

Oracle answers are not written by hand. Each instance under [qa_instances/](qa_instances/)
is **autoharvested**: we run the pinned, shape-only test inside the repo's Docker image
under a line-level tracer, then a per-instance `parse_*_oracle.py` script replays the trace
and computes the ground-truth `oracle_answer` deterministically. This guarantees the answer
reflects real runtime behavior rather than human assumption.

### Images

Every repository is harvested inside its own SWE-bench-style Docker image (pinned to a
specific commit/environment). The runner pulls the image automatically if it is not present
locally. Images are large; expect a one-time pull per repository.

| Repository      | Docker image |
|-----------------|--------------|
| Keras           | `starryzhang/sweb.eval.x86_64.keras-team_1776_keras-21072:latest` |
| Telegram_bot    | `starryzhang/sweb.eval.x86_64.python-telegram-bot_1776_python-telegram-bot-4673:latest` |
| Sympy           | `starryzhang/sweb.eval.x86_64.sympy_1776_sympy-27462:latest` |
| faker_qa        | `starryzhang/sweb.eval.x86_64.joke2k_1776_faker-2190:latest` |
| pydata_xarray   | `starryzhang/sweb.eval.x86_64.pydata_1776_xarray-10076:latest` |
| yt_dlp          | `starryzhang/sweb.eval.x86_64.yt-dlp_1776_yt-dlp-12714:latest` |
| matplotlib_qa   | `starryzhang/sweb.eval.x86_64.matplotlib_1776_matplotlib-29209:latest` |
| qtile           | `starryzhang/sweb.eval.x86_64.qtile_1776_qtile-5206` |
| cfnlint_qa      | `starryzhang/sweb.eval.x86_64.aws-cloudformation_1776_cfn-lint-4236:latest` |
| reflex_qa       | `starryzhang/sweb.eval.x86_64.reflex-dev_1776_reflex-5081` |

The same mapping is kept in [Repositories.json](Repositories.json).

### Running it for a repository

Each repository folder under `qa_instances/<repo>/` ships two host-side runners (run them
from inside that folder; they require Docker):

```bash
cd qa_instances/yt_dlp

# Harvest a single instance
./run_qa_fromhost.sh <instance_id>

# Harvest every instance in the repository
./run_all_qa_fromhost.sh
```

Each runner starts a fresh container from the repo's image, stages the QA scripts/files into
`/testbed`, runs `qa_pipeline.sh` for the instance (instrumented pytest + oracle parse),
copies the results back to the host, and removes the container. The image defaults to the
repo's entry in the table above and can be overridden with the `IMAGE` env var.

### What gets saved (`qa_artifacts/`)

Results land in `qa_instances/<repo>/qa_artifacts/<instance_id>/`, one folder per instance:

- `oracle.json` — the harvested QA record: `question_kind`, `question`, `template_answer`
  schema, and the ground-truth `oracle_answer`.
- `trace.log` — the line-level execution trace (per-line locals deltas) the answer is derived from.
- `pytest.log` — output of the shape-only test run.
- `oracle.log` — output of the oracle parse step.

## Citation & License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md).

This project references SWE-bench Live benchmark resources and Docker images.
Those third-party resources are not relicensed by this repository; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution and license
notes.
