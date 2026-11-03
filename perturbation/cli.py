"""Command-line entrypoint for the perturbation pipeline.

Examples
--------
Dry run (perturb + show, no Docker / no API calls) on a couple of Keras
instances::

    python -m perturbation --repo Keras --max-instances 2 \
        --no-harvest --no-inference --no-eval

Full loop on Keras passing instances with the default model::

    python -m perturbation --repo Keras --strategies boundary --seeds 7 13

Coverage-guided exploration (keep candidates that reach new branches)::

    python -m perturbation --repo Keras --explore
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import List

from .config import PerturbationConfig
from .models import InstanceOutcome
from .pipeline import PerturbationPipeline
from .strategies import available as available_strategies


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="perturbation",
        description="Generate harder QA instances by perturbing passing test inputs.",
    )
    p.add_argument("--repo", default="Keras", help="Repository under qa_instances/ (default: Keras)")
    p.add_argument(
        "--repos", nargs="+", default=None,
        help="Run over multiple repositories instead of --repo. Use 'all' for every repo under qa_instances/.",
    )
    p.add_argument("--tool", default="llm")
    p.add_argument("--vendor", default="openai")
    p.add_argument("--model", default="gpt-5.4-2026-03-05")

    p.add_argument(
        "--strategies", nargs="+", default=["boundary"],
        help=f"Perturbation strategies to try. Available: {', '.join(available_strategies())}",
    )
    p.add_argument("--seeds", nargs="+", type=int, default=[7], help="Random seeds to try per strategy")
    p.add_argument("--magnitude", type=float, default=1.0, help="Perturbation strength knob")
    p.add_argument(
        "--preserve-length", action=argparse.BooleanOptionalAction, default=True,
        help="Keep perturbed vectors the same length (avoids breaking shape-coupled "
             "code). Default: on.",
    )
    p.add_argument(
        "--assertion-policy", choices=["neutralize", "keep"], default="neutralize",
        help="How to handle the test's own assertions (default: neutralize)",
    )

    p.add_argument(
        "--instance-ids", nargs="+", default=None,
        help="Explicit instance ids to consider (default: all in repo)",
    )
    p.add_argument("--max-instances", type=int, default=None, help="Cap number of source instances")
    p.add_argument(
        "--max-per-repo", type=int, default=None,
        help="Before perturbation, select at most N original instances from each repo.",
    )
    p.add_argument(
        "--include-failing", action="store_true",
        help="Also perturb instances the model already fails (default: only passing)",
    )

    # Stage toggles (all on by default; use --no-* to skip).
    p.add_argument("--harvest", dest="run_harvest", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--inference", dest="run_inference", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--eval", dest="run_eval", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument(
        "--stop-on-first-flip", action=argparse.BooleanOptionalAction, default=False,
        help="Stop trying candidates for an instance once one flips to failing",
    )
    p.add_argument("--overwrite", dest="overwrite_existing", action="store_true")

    p.add_argument(
        "--inference-conda-env", default="repo",
        help="Conda env to run the LLM runner in (needs aider-chat). Default: repo",
    )
    p.add_argument(
        "--inference-python", default=None,
        help="Explicit python interpreter for the LLM runner (overrides --inference-conda-env)",
    )
    p.add_argument("--image", default=None, help="Override IMAGE for run_qa_fromhost.sh")
    p.add_argument("--harvest-timeout", type=int, default=1000)
    p.add_argument("--inference-timeout", type=int, default=440)
    p.add_argument(
        "--inference-extra", nargs=argparse.REMAINDER, default=[],
        help="Extra args passed verbatim to run_llm_repomap_eval_host.py (must be last)",
    )

    # -- LLM-based perturbation -----------------------------------------------
    p.add_argument(
        "--llm-perturb", action="store_true",
        help="Use an LLM to propose N structure-preserving perturbed test sources "
             "per instance (reuses the repo read tools). Run under the 'repo' conda "
             "env so the provider SDK is available.",
    )
    p.add_argument("--llm-n", type=int, default=5, help="Variants per instance (default 5)")
    p.add_argument("--llm-provider", default=None, help="LLM provider (default: --vendor)")
    p.add_argument("--llm-model", default=None, help="LLM model (default: --model)")
    p.add_argument("--llm-temperature", type=float, default=0.0)
    p.add_argument(
        "--llm-threads", type=int, default=1,
        help="Parallel threads for LLM variant generation (OpenAI calls). "
             "Harvesting stays serial (shared container).",
    )

    # -- coverage-guided exploration ------------------------------------------
    p.add_argument(
        "--explore", action="store_true",
        help="Coverage-guided search: keep multiple perturbations per instance, "
             "each reaching new branches.",
    )
    p.add_argument(
        "--explore-strategies", nargs="+",
        default=["boundary", "threshold_straddle", "special_value"],
        help="Mutation operators tried during exploration.",
    )
    p.add_argument("--explore-seeds", nargs="+", type=int, default=list(range(8)))
    p.add_argument("--explore-budget", type=int, default=12, help="Max harvest attempts per instance")
    p.add_argument(
        "--explore-max-keep", type=int, default=4,
        help="Deprecated; all harvested candidates are saved.",
    )
    p.add_argument(
        "--explore-require-new-coverage", action=argparse.BooleanOptionalAction, default=True,
        help="Deprecated as a retention gate; still affects the informational coverage stage status.",
    )
    p.add_argument(
        "--accept-on", choices=["coverage", "oracle-change", "flip"], default="coverage",
        help="Deprecated as a retention gate. All harvested perturbations are saved; "
             "coverage/oracle-change/flip are reported as per-instance booleans.",
    )
    p.add_argument(
        "--explore-baseline", action=argparse.BooleanOptionalAction, default=True,
        help="Harvest the original once to establish a coverage baseline",
    )
    p.add_argument(
        "--target-source-root", default=None,
        help="Existing repo source checkout for parsing the function under test "
             "for thresholds. If unset, the source is materialized from the eval "
             "image (see --materialize-source).",
    )
    p.add_argument(
        "--materialize-source", action=argparse.BooleanOptionalAction, default=True,
        help="Materialize the repo source from its eval image (Docker) to read "
             "the function under test for thresholds (default: on).",
    )
    p.add_argument(
        "--snapshot-root", default=None,
        help="Where to materialize repo source snapshots "
             "(default: perturbation/.tmp_mounted_repos).",
    )
    p.add_argument(
        "--cleanup-snapshot", action=argparse.BooleanOptionalAction, default=True,
        help="Remove the materialized source snapshot when the pipeline finishes.",
    )

    p.add_argument(
        "--output-root", default=None,
        help="Where generated instances + evaluations are stored "
             "(default: perturbation/generated)",
    )
    p.add_argument(
        "--progress", action=argparse.BooleanOptionalAction, default=True,
        help="Print live progress while running (default: on).",
    )
    p.add_argument(
        "--report", default=None,
        help="Write a JSON report with all attempts, generated instances, and gate-result annotations.",
    )
    p.add_argument(
        "--feedback-from-report", default=None,
        help="Run the post-perturbation LLM feedback loop from an existing perturbation report.",
    )
    p.add_argument(
        "--feedback-input-root", default=None,
        help="Input generated artifact root for --feedback-from-report "
             "(default: --output-root if set, else perturbation/generated).",
    )
    p.add_argument(
        "--feedback-output-root", default="perturbation/generated_feedback",
        help="Separate output root for feedback results (default: perturbation/generated_feedback).",
    )
    p.add_argument(
        "--feedback-iterations", type=int, default=5,
        help="Max LLM feedback iterations per non-flipping generated instance (default: 5).",
    )
    p.add_argument(
        "--sample-per-category", type=int, default=None,
        help="Before perturbation, select at most N original instances per "
             "question_kind taxonomy category across all selected repos.",
    )
    return p


def config_from_args(args: argparse.Namespace) -> PerturbationConfig:
    return PerturbationConfig(
        repo=args.repo,
        tool=args.tool,
        vendor=args.vendor,
        model=args.model,
        strategies=args.strategies,
        seeds=args.seeds,
        magnitude=args.magnitude,
        preserve_length=args.preserve_length,
        assertion_policy=args.assertion_policy,
        instance_ids=args.instance_ids,
        max_instances=args.max_instances,
        max_per_repo=args.max_per_repo,
        only_passing=not args.include_failing,
        run_harvest=args.run_harvest,
        run_inference=args.run_inference,
        run_eval=args.run_eval,
        sample_per_category=args.sample_per_category,
        stop_on_first_flip=args.stop_on_first_flip,
        overwrite_existing=args.overwrite_existing,
        image=args.image,
        harvest_timeout=args.harvest_timeout,
        inference_timeout=args.inference_timeout,
        inference_extra_args=list(args.inference_extra or []),
        inference_python=args.inference_python,
        inference_conda_env=args.inference_conda_env,
        output_root=args.output_root,
        explore=args.explore,
        explore_strategies=args.explore_strategies,
        explore_seeds=args.explore_seeds,
        explore_budget=args.explore_budget,
        explore_max_keep=args.explore_max_keep,
        explore_require_new_coverage=args.explore_require_new_coverage,
        accept_criterion={"oracle-change": "oracle", "flip": "flip"}.get(args.accept_on, "coverage"),
        llm_perturb=args.llm_perturb,
        llm_n=args.llm_n,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_temperature=args.llm_temperature,
        llm_threads=args.llm_threads,
        explore_baseline=args.explore_baseline,
        target_source_root=args.target_source_root,
        materialize_source=args.materialize_source,
        snapshot_root=args.snapshot_root,
        cleanup_snapshot=args.cleanup_snapshot,
        progress=args.progress,
    )


def _print_summary(outcomes: List[InstanceOutcome]) -> None:
    produced = [o for o in outcomes if o.persisted]
    flipped = [o for o in produced if o.flipped_to_fail]
    harvested_failed = [o for o in outcomes if not o.harvested]
    print("\n=== Perturbation summary ===")
    print(f"attempts:          {len(outcomes)}")
    print(f"instances created: {len(produced)}")
    print(f"harvest failures:  {len(harvested_failed)}")
    print(f"flipped to fail:   {len(flipped)}")
    for o in produced:
        flip = {True: "FLIP->FAIL", False: "still-pass", None: "n/a"}[o.flipped_to_fail]
        cov = ""
        if o.new_lines_vs_baseline is not None:
            cov = f"  +lines={o.new_lines_vs_baseline} +edges={o.new_edges_vs_baseline}"
        trace = {True: "same-trace", False: "different-trace", None: "trace-n/a"}[o.trace_same_as_original]
        print(
            f"- {o.repo}/{o.new_id}  changes={o.n_changes}  "
            f"oracle_changed={o.oracle_changed}  {trace}{cov}  {flip}"
        )


def _count_by_question_kind(outcomes: List[InstanceOutcome]) -> dict:
    return dict(sorted(Counter(o.question_kind or "UNKNOWN" for o in outcomes).items()))


def _build_report(outcomes: List[InstanceOutcome]) -> dict:
    generated = [o for o in outcomes if o.persisted]
    harvest_failed = [o for o in outcomes if not o.harvested]
    return {
        "summary": {
            "attempts": len(outcomes),
            "generated_instances": len(generated),
            "harvest_failures": len(harvest_failed),
            "flipped_to_fail": sum(1 for o in generated if o.flipped_to_fail),
            "oracle_changed": sum(1 for o in generated if o.oracle_changed),
            "same_oracle": sum(1 for o in generated if o.same_oracle),
            "different_trace": sum(1 for o in generated if o.trace_changed),
            "same_trace": sum(1 for o in generated if o.trace_same_as_original),
        },
        "question_kind_counts": {
            "attempts": _count_by_question_kind(outcomes),
            "generated_instances": _count_by_question_kind(generated),
            "harvest_failures": _count_by_question_kind(harvest_failed),
        },
        "attempts": [o.to_dict() for o in outcomes],
        "generated_instances": [o.to_dict() for o in generated],
    }


def _resolve_repos(args: argparse.Namespace) -> List[str]:
    if not args.repos:
        return [args.repo]
    if len(args.repos) == 1 and args.repos[0].lower() == "all":
        from .paths import RepoLayout
        layout = RepoLayout()
        if not layout.qa_root.exists():
            return []
        return sorted(
            child.name
            for child in layout.qa_root.iterdir()
            if child.is_dir() and child.name not in {"shared", "qa_artifacts"}
        )
    return args.repos


def _question_kind_for(repo: str, instance_id: str) -> str:
    from .paths import RepoLayout
    layout = RepoLayout()
    oracle = layout.oracle_path(repo, instance_id)
    try:
        data = json.loads(oracle.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return "UNKNOWN"
    if isinstance(data, dict):
        return str(data.get("question_kind") or "UNKNOWN")
    return "UNKNOWN"


def _sample_instance_plan(args: argparse.Namespace, repos: List[str]) -> dict[str, List[str]] | None:
    """Pick at most N original instances per question_kind across all repos."""
    n = args.sample_per_category
    if n is None:
        return None
    if n <= 0:
        return {repo: [] for repo in repos}

    from .paths import RepoLayout
    from .selection import InstanceClassifier

    counts: Counter[str] = Counter()
    plan: dict[str, List[str]] = {repo: [] for repo in repos}
    max_per_repo = None if args.max_per_repo is None else max(0, args.max_per_repo)
    layout = RepoLayout()

    for repo in repos:
        config = config_from_args(args)
        config.repo = repo
        config.sample_per_category = None
        classifier = InstanceClassifier(config, layout)
        report = classifier.classify_repo(repo, args.instance_ids)
        candidates = report.passing_ids if config.only_passing else [
            c.instance_id for c in report.classifications
        ]
        for instance_id in candidates:
            if max_per_repo is not None and len(plan[repo]) >= max_per_repo:
                break
            kind = _question_kind_for(repo, instance_id)
            if counts[kind] >= n:
                continue
            counts[kind] += 1
            plan[repo].append(instance_id)

    if args.progress:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"[sample] selected by question_kind across repos: {detail}", flush=True)
    return plan


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Load .env so in-process LLM calls (--llm-perturb) pick up provider API keys.
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except Exception:  # noqa: BLE001
        pass
    if args.feedback_from_report:
        from .feedback import run_feedback_from_report

        config = config_from_args(args)
        config.output_root = args.feedback_output_root
        if args.report:
            report_path = Path(args.report)
        else:
            report_path = Path(args.feedback_output_root) / "reports" / "feedback_report.json"
        feedback_input_root = args.feedback_input_root or args.output_root
        if feedback_input_root is None:
            feedback_report_path = Path(args.feedback_from_report)
            if feedback_report_path.parent.name == "reports":
                feedback_input_root = str(feedback_report_path.parent.parent)
        payload = run_feedback_from_report(
            base_config=config,
            input_report=args.feedback_from_report,
            input_root=feedback_input_root,
            output_root=args.feedback_output_root,
            iterations=args.feedback_iterations,
            report_path=str(report_path),
        )
        print("\n=== Feedback summary ===")
        for key, value in payload["summary"].items():
            print(f"{key}: {value}")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\nFeedback report written to: {report_path}")
        return 0

    outcomes: List[InstanceOutcome] = []
    repos = _resolve_repos(args)
    sampled_plan = _sample_instance_plan(args, repos)
    for repo in repos:
        config = config_from_args(args)
        config.repo = repo
        if sampled_plan is not None:
            config.instance_ids = sampled_plan.get(repo, [])
            config.sample_per_category = None
        pipeline = PerturbationPipeline(config)
        outcomes.extend(pipeline.run())
    _print_summary(outcomes)

    if args.report:
        payload = _build_report(outcomes)
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(
            f"\nReport written to: {report_path} "
            f"({len(payload['generated_instances'])} generated instances)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
