# perturbation

Generate **harder** QA instances by perturbing the *inputs* of existing test
cases, re-harvesting a fresh oracle, and checking whether the same model now
**fails** an instance it previously answered correctly.

Two perturbation engines, same downstream pipeline:

- **Deterministic (AST, no LLM)** — boundary/edge-case mutation of input
  literals. Cheap, reproducible (seeded), and the default.
- **LLM (`--llm-perturb`)** — an LLM rewrites the test's concrete input values
  (any type) while preserving structure, using read-only repo tools. A smarter
  *proposer* for semantically-constrained repos; the oracle and validation are
  unchanged.

## Idea

For each target instance (passing by default; add `--include-failing` for all):

1. **Perturb** the test's concrete input values (AST or LLM).
2. **Re-harvest** a fresh `oracle.json` with the existing pipeline
   (`run_qa_fromhost.sh` → `qa_pipeline.sh` → `eval.sh` → `parse_*_oracle.py`).
3. **Rebuild** the `qa_instances_eval` question and **run inference** with the
   target model.
4. **Score** the answer (reusing `evaluate_qa_answers`) to see if the instance
   flipped pass → fail.

> The harvesting pipeline is its own validator: a perturbation that breaks
> execution produces no oracle, so it is rolled back and the next candidate is
> tried. Only perturbations that yield a valid, fresh oracle survive.

### Where things are stored

Generated artifacts are kept **separate from the main benchmark**, under a single
self-contained output root (default `perturbation/generated/`):

```
perturbation/generated/
  qa_instances/<repo>/<id>/            # perturbed test + eval.sh + parser + fresh oracle.json
  qa_instances_eval/<repo>/<id>/       # question.json + test (model input)
  evaluations/llm/<vendor>/<model>/<repo>/<id>/   # answer.json + usage.json + ...
```

A perturbed instance keeps the original test file name, class, and method (so the
question text and parser logic still match); only the directory name, the input
values, and the harvested oracle differ. The id is
`<original_id>__pert_<strategy>_s<seed>` (AST) or `<original_id>__pert_llm_s<i>`.
The harvested `oracle.json` also gets a `template_answer` schema (via
`make_template_answers.to_template`) so the model is told the expected output
shape.

> **Harvest note:** `run_qa_fromhost.sh` requires the instance to physically live
> under `qa_instances/<repo>/` while its container runs. The pipeline therefore
> materializes + harvests the instance there, then **moves** it into the output
> tree and cleans up `qa_artifacts/`, so the main benchmark trees are never left
> modified. Override the location with `--output-root`.

## Deterministic perturbation (AST)

Inputs are perturbed toward **branch boundaries and edge cases** while
**structure is protected**:

- `threshold_straddle`: boundary value analysis — sets values just-below / at /
  just-above the code's comparison constants (e.g. a ReLU test's
  `threshold`/`max_value`), plus zero / negative / large. Thresholds come from
  the test's own literals and from the function under test (see source
  materialization below).
- `special_value`: injects control-flow-flipping specials (zero, sign flip, very
  small / very large; non-finite optional) to trip `is None` / `== 0` / `< 0` /
  empty-vs-nonempty branches.
- `boundary` (default): composite of `threshold_straddle` + `special_value`.

Vector perturbations are **length-preserving by default** (`--preserve-length`):
each element is mapped onto a boundary in place, so shape-coupled code (an array
whose length must match another's axis) keeps working. Use `--no-preserve-length`
to allow resizing.

## LLM perturbation (`--llm-perturb`)

An LLM proposes `--llm-n` (default 5) structure-preserving variants per instance:
it may change concrete input values of *any* type, must keep imports / class /
method names / call order / assertions, and is told to target edge cases that
reach new branches. It can use the read-only repo tools (`get_repo_map`,
`list_dir`, `read_file`) — reused from `evaluation_scripts/llm_eval/repo_tools.py`
— to read the function under test first. Each variant is then harvested + gated
exactly like an AST candidate, so the LLM is only a *proposer*.

- Generation calls run in a thread pool (`--llm-threads`); harvesting stays
  serial (one shared container).
- Runs **in-process**, so launch under the `repo` conda env (provider SDK) and
  ensure the API key is set (`.env` is auto-loaded).
- LLM strength: it produces *valid* inputs that respect domain preconditions, so
  it works on constrained repos (e.g. python-control) where AST mutation crashes.

```bash
conda run -n repo python -m perturbation --repo python-control --llm-perturb \
    --llm-n 5 --llm-threads 5 --accept-on flip --include-failing \
    --output-root perturbation/generated_llm \
    --report perturbation/generated_llm/llm_python-control.json
```

## Acceptance gates (`--explore` / `--llm-perturb`)

Both engines run a budgeted search per instance and keep candidates by a gate:

- `--accept-on coverage` (default): keep candidates that reach **new branches**
  (novel coverage signature vs the original's baseline). Reads the execution
  `trace.log` (produced by `trace_plugin.py`).
- `--accept-on oracle-change`: keep candidates whose **harvested answer differs**
  from the original (dedups identical/unchanged oracles).
- `--accept-on flip`: ignore the above and keep **only** candidates the model
  goes **pass → fail** on. Runs inference+eval first, then rolls back non-flips.
  Requires inference + eval enabled (a flip needs the model's answer); it scores
  every harvested candidate, so it is the most API-costly gate.

```bash
python -m perturbation --repo Keras --explore \
    --explore-strategies boundary threshold_straddle special_value \
    --explore-budget 12 --explore-max-keep 4 --accept-on coverage \
    --report perturbation/generated/reports/explore_keras.json
```

### Source materialization (for thresholds + LLM tools)

By default the repo's source is materialized from its eval image (via Docker,
reusing the project's `materialize_repo_snapshot`) into
`perturbation/.tmp_mounted_repos/<repo>/`, used to (a) read comparison constants
from the function under test (`threshold_straddle`) and (b) back the LLM read
tools. It is removed when the pipeline finishes.

- `--target-source-root PATH` — use an existing checkout instead of materializing.
- `--no-materialize-source` — skip it (test-file literals only; no Docker).
- `--snapshot-root PATH` / `--no-cleanup-snapshot` — change location / keep it.

## Usage

Dry run (perturb only — no Docker, no API):

```bash
python -m perturbation --repo Keras --max-instances 3 \
    --no-harvest --no-inference --no-eval --no-materialize-source
```

One-shot deterministic loop (needs Docker + provider API key):

```bash
export OPENAI_API_KEY=...
python -m perturbation --repo Keras --strategies boundary --seeds 7 13 \
    --report perturbation/generated/reports/keras.json
```

Keep only model-flipping instances (AST or LLM):

```bash
python -m perturbation --repo matplotlib_qa --explore --accept-on flip \
    --include-failing --max-instances 10
```

### Key flags

| Flag | Meaning |
|---|---|
| `--repo` | Repository under `qa_instances/` (default `Keras`) |
| `--vendor` / `--model` | Target model to evaluate against (default openai / gpt-5.4) |
| `--strategies` | One-shot AST strategies: `boundary`, `threshold_straddle`, `special_value` |
| `--seeds` / `--magnitude` | Seeds per strategy; perturbation strength |
| `--preserve-length` / `--no-preserve-length` | Keep vector lengths (default on) |
| `--assertion-policy` | `neutralize` (default) or `keep` |
| `--explore` | Coverage-guided budgeted search (multiple kept per instance) |
| `--explore-strategies` / `--explore-seeds` | Operators / seeds tried while exploring |
| `--explore-budget` / `--explore-max-keep` | Max harvests / kept candidates per instance |
| `--accept-on` | `coverage` (default), `oracle-change`, or `flip` |
| `--llm-perturb` | Use the LLM proposer (run under the `repo` conda env) |
| `--llm-n` / `--llm-threads` | Variants per instance; parallel generation threads |
| `--llm-provider` / `--llm-model` / `--llm-temperature` | LLM overrides (default: `--vendor`/`--model`) |
| `--include-failing` | Also perturb already-failing instances |
| `--instance-ids` / `--max-instances` | Restrict the source instances |
| `--no-harvest/-inference/-eval` | Skip stages (dry runs / staging) |
| `--target-source-root` / `--no-materialize-source` | Source for thresholds + LLM tools |
| `--snapshot-root` / `--no-cleanup-snapshot` | Materialized-source location / keep it |
| `--harvest-timeout` | Per-harvest timeout in seconds (default 600) |
| `--image` | Override `IMAGE` for `run_qa_fromhost.sh` |
| `--inference-extra ...` | Pass-through args to the LLM runner (must be last) |
| `--output-root` | Where generated instances + evaluations are stored |
| `--progress` / `--no-progress` | Live per-instance/per-attempt progress (default on) |
| `--report PATH` | Write generated instances to JSON (failed/dropped excluded) |

Progress is printed live (one line per attempt). The final summary and the
`--report` JSON list **only the instances actually generated** — broken
perturbations (harvest failed), explore drops (no new coverage / unchanged
oracle), and flip-gate non-flips are counted but not written.

## Repository fit (empirical)

The approach yields when test inputs are **free numeric data feeding the traced
computation**, and struggles when they are **constrained parameters/structure**:

- **Good** (deterministic works): `Keras`, `matplotlib_qa`.
- **Constrained** (AST crashes / answers don't move; the **LLM** helps because it
  produces valid inputs): `python-control` (algorithm preconditions),
  `pydata_xarray` (coordinate coupling + dates), `Telegram_bot` (dates/ids/strings).
- **Low numeric / string-enum** (sparse yield): `Sympy`, `yt_dlp`, `faker_qa`,
  `cfnlint_qa`, `reflex_qa`, `qtile`.

A common ceiling for both engines: **invariant/boolean oracles** (e.g.
`invariant_exists`) that don't change under input perturbation.


## Design (extension points)

```
perturbation/
  generated/         output: perturbed instances + their evaluations
  config.py          PerturbationConfig + structural protection sets
  paths.py           DataLayout / RepoLayout (source) / OutputLayout (generated)
  models.py          result/value objects
  selection.py       InstanceClassifier  (reuses evaluate_qa_answers)
  astutil.py         shared AST helpers (signed-literal / call-name)
  analysis.py        TargetAnalyzer: branch thresholds from test/target source
  snapshot.py        RepoSnapshotManager: materialize repo source from eval image
  coverage.py        CoverageExtractor + CoverageSignature (parses trace.log)
  explorer.py        CoverageGuidedExplorer: budgeted search + gates
  llm_strategy.py    LLMPerturber: LLM source-level variant generation
  strategies/        Strategy pattern + registry/factory (AST)
    base.py          PerturbationStrategy ABC + PerturbationContext
    boundary.py      ThresholdStraddleStrategy / SpecialValueStrategy
    composite.py     CompositeStrategy (chains constant + sequence hooks)
    registry.py      create() / register() / available()
  assertions.py      AssertionPolicy (keep / neutralize)
  perturber.py       TestPerturber: AST driver (structural protection)
  materializer.py    new instance dir + eval.sh rewrite + relocate to output
  harvest.py         OracleHarvester (wraps run_qa_fromhost.sh; embeds template)
  dataset.py         EvalDatasetBuilder (reuses make_qa_instances_eval)
  inference.py       InferenceRunner (wraps the LLM runner)
  pipeline.py        PerturbationPipeline orchestrator
  cli.py / __main__  CLI
```

Add a new AST perturbation by subclassing `PerturbationStrategy` and calling
`strategies.register("my_strategy", lambda m: MyStrategy(m))`. Add a new
assertion policy by subclassing `AssertionPolicy`, or a new acceptance gate in
`explorer.py`. Everything is repo-agnostic — pass `--repo <other>` to run on any
of the 12 repositories.
```
