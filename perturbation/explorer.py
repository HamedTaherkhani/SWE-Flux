"""Coverage-guided exploration.

Instead of one perturbation per instance, the explorer runs a budgeted search:
it tries many (strategy, seed) mutations, harvests each, reads the execution
trace, and **keeps only perturbations that reach new branches/paths** -- novel
coverage signatures, and (optionally) lines not in the original's baseline. The
result is a small set of perturbed instances per original, each exercising a
different path through the code under test.

The harvest step is the fitness evaluator (a perturbation that breaks execution
yields no trace and is discarded). This is greybox/coverage-guided fuzzing
applied to test inputs, with the existing trace as feedback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from .coverage import CoverageExtractor, CoverageSignature
from .models import InstanceOutcome

if TYPE_CHECKING:  # avoid import cycle at runtime
    from .pipeline import PerturbationPipeline


class CoverageGuidedExplorer:
    def __init__(self, pipeline: "PerturbationPipeline") -> None:
        self.p = pipeline
        self.config = pipeline.config
        self.extractor = CoverageExtractor()

    # -- baseline --------------------------------------------------------------
    def _baseline_coverage(self, original_id: str) -> CoverageSignature:
        """Harvest a throwaway copy of the original (unperturbed) to get its
        coverage, without disturbing the canonical instance."""
        if not (self.config.explore_baseline and self.config.run_harvest):
            return CoverageSignature()
        repo = self.config.repo
        tmp_id = f"{original_id}__baseline_tmp"
        try:
            # A copy of the original with inputs unchanged: its assertions still
            # pass and its trace is the unperturbed coverage baseline.
            self.p.materializer.materialize(repo, original_id, tmp_id)
            harvest = self.p.harvester.harvest(repo, tmp_id)
            if harvest.ok and harvest.trace_path:
                return self.extractor.extract_file(harvest.trace_path) or CoverageSignature()
            return CoverageSignature()
        except Exception:  # noqa: BLE001
            return CoverageSignature()
        finally:
            self.p.materializer.remove(repo, tmp_id)

    # -- main search -----------------------------------------------------------
    def explore(self, original_id: str, original_passed: bool) -> List[InstanceOutcome]:
        # Source-derived thresholds are wired into the perturber by the pipeline's
        # _materialize_perturb step, so the explorer only drives the search.
        baseline = self._baseline_coverage(original_id)
        self.p._log(f"    baseline coverage: {len(baseline.lines)} lines")  # noqa: SLF001

        seen: set[int] = set()
        all_outcomes: List[InstanceOutcome] = []
        kept_count = 0
        attempts = 0

        for strategy in self.config.explore_strategies:
            for seed in self.config.explore_seeds:
                if attempts >= self.config.explore_budget or kept_count >= self.config.explore_max_keep:
                    return all_outcomes
                attempts += 1
                outcome = self._one(original_id, strategy, seed, original_passed, baseline, seen)
                all_outcomes.append(outcome)
                if outcome.kept:
                    kept_count += 1
                self.p._log("    " + self.p._fmt_outcome(outcome))  # noqa: SLF001
        return all_outcomes

    def _one(
        self,
        original_id: str,
        strategy: str,
        seed: int,
        original_passed: bool,
        baseline: CoverageSignature,
        seen: set,
        source: str = None,
    ) -> InstanceOutcome:
        """Run one mutation attempt; always returns an outcome with ``kept`` set.

        If ``source`` is given it is used verbatim (e.g. an LLM-proposed variant);
        otherwise the AST strategy generates the perturbation.
        """
        repo = self.config.repo
        new_id = self.config.new_instance_id(original_id, strategy, seed)
        outcome = InstanceOutcome(
            repo=repo, original_id=original_id, new_id=new_id,
            strategy=strategy, seed=seed, model_passed_original=original_passed,
        )

        if source is None:
            materialized = self.p._materialize_perturb(original_id, new_id, strategy, seed, outcome)  # noqa: SLF001
        else:
            materialized = self.p._materialize_source(original_id, new_id, source, outcome)  # noqa: SLF001
        if materialized is None:
            outcome.kept = False
            return outcome
        harvest = self.p._harvest_step(original_id, new_id, outcome)  # noqa: SLF001
        if harvest is None:
            outcome.kept = False
            return outcome

        # Always record coverage metrics (useful in the report either way).
        sig = (self.extractor.extract_file(harvest.trace_path) if harvest.trace_path else None) or CoverageSignature()
        outcome.covered_lines = len(sig.lines)
        outcome.new_lines_vs_baseline = len(sig.new_lines_vs(baseline))
        outcome.new_edges_vs_baseline = len(sig.new_edges_vs(baseline))

        # flip gate: ignore other gates -- finalize (relocate + dataset +
        # inference + eval) first, then keep ONLY if the model went pass -> fail.
        if self.config.accept_criterion == "flip":
            self.p._finalize(new_id, outcome)  # noqa: SLF001
            if outcome.flipped_to_fail:
                outcome.add_stage("flip", True, "pass->fail")
                outcome.kept = True
            else:
                outcome.add_stage("flip", False, f"no flip (new_pass={outcome.model_passed_new})")
                self.p._remove_output_instance(new_id)  # noqa: SLF001
                self.p.materializer.remove(repo, new_id)  # if relocate didn't happen  # noqa: SLF001
                outcome.kept = False
            return outcome

        # acceptance gate -------------------------------------------------------
        if self.config.accept_criterion == "oracle":
            accept, stage_ok_detail, stage_bad_detail = self._oracle_gate(new_id, outcome, seen)
        else:
            accept, stage_ok_detail, stage_bad_detail = self._coverage_gate(sig, baseline, seen)

        if not accept:
            outcome.add_stage(self.config.accept_criterion, False, stage_bad_detail)
            self.p.materializer.remove(repo, new_id)
            outcome.kept = False
            return outcome

        outcome.add_stage(self.config.accept_criterion, True, stage_ok_detail)
        outcome.kept = True
        return self.p._finalize(new_id, outcome)  # noqa: SLF001

    def _coverage_gate(self, sig: CoverageSignature, baseline: CoverageSignature, seen: set):
        new_lines = sig.new_lines_vs(baseline)
        new_edges = sig.new_edges_vs(baseline)
        novel = sig.key not in seen
        reaches_new = bool(new_lines or new_edges)
        if not (novel and (reaches_new or not self.config.explore_require_new_coverage)):
            return False, "", ("duplicate coverage" if not novel else "no new branches vs baseline")
        seen.add(sig.key)
        return True, f"+{len(new_lines)} lines / +{len(new_edges)} edges (total {len(sig.lines)})", ""

    def _oracle_gate(self, new_id: str, outcome: InstanceOutcome, seen: set):
        """Accept if the harvested oracle differs from the original and is not a
        duplicate of one we've already kept for this instance."""
        if not outcome.oracle_changed:
            return False, "", "oracle unchanged"
        try:
            import json
            from perturbation.paths import ensure_repo_on_path
            ensure_repo_on_path()
            from evaluation_scripts import evaluate_qa_answers as eqa
            answer = eqa.load_json(self.p.source.oracle_path(self.config.repo, new_id)).get("oracle_answer")
            key = json.dumps(answer, sort_keys=True, default=str)
        except Exception:  # noqa: BLE001
            key = None
        if key is not None and key in seen:
            return False, "", "duplicate oracle"
        if key is not None:
            seen.add(key)
        return True, "oracle changed", ""
