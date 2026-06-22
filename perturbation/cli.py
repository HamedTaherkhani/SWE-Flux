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
        "--include-failing", action="store_true",
        help="Also perturb instances the model already fails (default: only passing)",
    )

    # Stage toggles (all on by default; use --no-* to skip).
    p.add_argument("--harvest", dest="run_harvest", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--inference", dest="run_inference", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--eval", dest="run_eval", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument(
        "--stop-on-first-flip", action=argparse.BooleanOptionalAction, default=True,
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
    p.add_argument("--harvest-timeout", type=int, default=600)
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
    p.add_argument("--llm-temperature", type=float, default=0.7)
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
    p.add_argument("--explore-max-keep", type=int, default=4, help="Max kept candidates per instance")
    p.add_argument(
        "--explore-require-new-coverage", action=argparse.BooleanOptionalAction, default=True,
        help="Keep a candidate only if it hits branches not in the original baseline",
    )
    p.add_argument(
        "--accept-on", choices=["coverage", "oracle-change", "flip"], default="coverage",
        help="Acceptance gate in explore mode: 'coverage' (new branches, default), "
             "'oracle-change' (answer differs from original), or 'flip' (keep ONLY if "
             "the model goes pass->fail; ignores the other gates, requires inference+eval)",
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
        help="Write a JSON report of generated instances to this path "
             "(failed/dropped attempts are excluded)",
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
        only_passing=not args.include_failing,
        run_harvest=args.run_harvest,
        run_inference=args.run_inference,
        run_eval=args.run_eval,
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
    # Only real, generated instances are reported; failed/dropped attempts are
    # summarized by count but not listed.
    produced = [o for o in outcomes if o.persisted]
    flipped = [o for o in produced if o.flipped_to_fail]
    print("\n=== Perturbation summary ===")
    print(f"attempts:          {len(outcomes)}")
    print(f"instances created: {len(produced)}")
    print(f"flipped to fail:   {len(flipped)}")
    for o in produced:
        flip = {True: "FLIP->FAIL", False: "still-pass", None: "n/a"}[o.flipped_to_fail]
        cov = ""
        if o.new_lines_vs_baseline is not None:
            cov = f"  +lines={o.new_lines_vs_baseline} +edges={o.new_edges_vs_baseline}"
        print(f"- {o.new_id}  changes={o.n_changes}  oracle_changed={o.oracle_changed}{cov}  {flip}")


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Load .env so in-process LLM calls (--llm-perturb) pick up provider API keys.
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except Exception:  # noqa: BLE001
        pass
    config = config_from_args(args)
    pipeline = PerturbationPipeline(config)
    outcomes = pipeline.run()
    _print_summary(outcomes)

    if args.report:
        # Report only real, generated instances (exclude failed/dropped attempts).
        payload = [o.to_dict() for o in outcomes if o.persisted]
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\nReport written to: {report_path} ({len(payload)} instances)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
