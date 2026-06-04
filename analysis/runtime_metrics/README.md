# Benchmark dynamic statistics (per QA instance)

Measures the runtime characteristics each RepoBehave QA instance exercises, then
reports **min / median / max (mean)** aggregated per repository and per question
category. It does **not** emit per-instance numbers.

Metrics (measured while the instance's exact oracle test runs):

| metric | meaning |
|---|---|
| `function_calls` | total in-repo function-call events |
| `distinct_functions` | distinct in-repo functions entered |
| `lines_covered` | distinct in-repo source lines executed |
| `files_covered` | distinct in-repo files touched |
| `classes_covered` | distinct in-repo classes whose methods ran |
| `max_stack_depth` | deepest in-repo call stack reached |
| `total_lines_executed` | line events incl. loop re-execution (iteration intensity) |

## Scope rules (what counts as "the repo")

Tracing uses `sys.settrace`, which only fires on **Python** frames, so C builtins
(`len`, `sum`, `count`, `print`, …) never appear. A frame counts only if its file
is under the repo checkout (`/testbed`) and is **not** in `site-packages`
(other libraries), the QA staging dir, or test scaffolding (`*_test.py`,
`/test/`, `/tests/`, `/testing/`, `conftest.py`). So only the target repo's own
library code is measured. Classes are counted only when the class is defined in a
repo file (filters `numpy`/`tf`/builtin objects sitting in `self`).

Each instance is driven by the exact `TEST_ID` from its `eval.sh` (the same test
the oracle harvests). Instances whose `TEST_ID` is a whole test class/file fold
their test cases together (counts summed, distinct sets unioned, depth maxed).

## Edge cases handled

- **Tests that raise** (exception-region QA instances): metrics are written after
  the call phase regardless of pass/fail, so the run up to the raise is recorded.
- **Generic test filenames** (`testcase.py` reused across instances, e.g.
  faker/cfnlint): such instances would overwrite each other if staged together,
  so they are detected and run one at a time in isolation.
- **Heterogeneous `TEST_ID` forms**: bare file (`testcase.py`), node id
  (`f.py::Class::method`), repo-relative, or full host-style path. Only the
  basename is trusted; the node id is rebuilt from the file actually staged.
- **Project venvs** (e.g. reflex installs pytest in `/testbed/.venv`): the
  collector uses `<repo>/.venv/bin/python` when present.
- `--continue-on-collection-errors` keeps one bad import/id from zeroing a repo.

## Usage

```bash
# 1. Harvest raw per-test metrics inside the repo's Docker image (one repo).
./analysis/runtime_metrics/run_repo.sh Keras
# repeat per repo, e.g.: for r in Sympy faker_qa yt_dlp ...; do ./run_repo.sh "$r"; done

# 2. Aggregate everything harvested under raw/ into the report.
python3 analysis/runtime_metrics/aggregate.py            # all repos in raw/
python3 analysis/runtime_metrics/aggregate.py --repo Keras
```

Outputs:
- `raw/<repo>.json` — per-test metrics (intermediate).
- `report.json` / `report.md` — min/median/max(mean) per repo, per category, overall.

## Files

- `metrics_plugin.py` — pytest plugin; traces each test, writes per-test metrics.
- `incontainer_collect.py` — runs in the container: stages files, resolves
  `TEST_ID`s, runs pytest with the plugin.
- `run_repo.sh` — host runner: starts the repo image, runs the collector, copies
  `raw/<repo>.json` back.
- `aggregate.py` — host aggregator and report renderer.
