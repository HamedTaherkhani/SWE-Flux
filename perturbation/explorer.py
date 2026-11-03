"""Perturbation exploration with saved gate annotations.

Instead of one perturbation per instance, the explorer runs a budgeted search:
it tries many (strategy, seed) mutations, harvests each, reads the execution
trace, and saves every candidate whose oracle harvest succeeds. Coverage,
oracle-change, and flip are recorded as per-candidate facts instead of being
used as retention gates.

The harvest step is the fitness evaluator (a perturbation that breaks execution
yields no trace/oracle and is not saved).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from .coverage import CoverageSignature
from .models import InstanceOutcome

if TYPE_CHECKING:  # avoid import cycle at runtime
    from .pipeline import PerturbationPipeline


class CoverageGuidedExplorer:
    def __init__(self, pipeline: "PerturbationPipeline") -> None:
        self.p = pipeline
        self.config = pipeline.config

    # -- baseline --------------------------------------------------------------
    def _baseline_coverage(self, original_id: str) -> CoverageSignature:
        """Harvest a throwaway copy of the original (unperturbed) to get its
        coverage, without disturbing the canonical instance."""
        return self.p.baseline_coverage(original_id)

    # -- main search -----------------------------------------------------------
    def explore(self, original_id: str, original_passed: bool) -> List[InstanceOutcome]:
        # Source-derived thresholds are wired into the perturber by the pipeline's
        # _materialize_perturb step, so the explorer only drives the search.
        baseline = self._baseline_coverage(original_id)
        self.p._log(f"    baseline coverage: {len(baseline.lines)} lines")  # noqa: SLF001

        seen: set[int] = set()
        all_outcomes: List[InstanceOutcome] = []
        attempts = 0

        for strategy in self.config.explore_strategies:
            for seed in self.config.explore_seeds:
                if attempts >= self.config.explore_budget:
                    return all_outcomes
                attempts += 1
                outcome = self._one(original_id, strategy, seed, original_passed, baseline, seen)
                all_outcomes.append(outcome)
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
        """Run one mutation attempt; harvested candidates are finalized and saved.

        If ``source`` is given it is used verbatim (e.g. an LLM-proposed variant);
        otherwise the AST strategy generates the perturbation.
        """
        repo = self.config.repo
        new_id = self.config.new_instance_id(original_id, strategy, seed)
        outcome = InstanceOutcome(
            repo=repo, original_id=original_id, new_id=new_id,
            strategy=strategy, seed=seed, model_passed_original=original_passed,
            model=self.config.model, question_kind=self.p._question_kind(original_id),  # noqa: SLF001
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

        sig = self.p._record_trace_comparison(original_id, harvest, outcome, baseline)  # noqa: SLF001
        self._record_gate_stages(new_id, outcome, sig, baseline, seen)
        outcome.kept = True
        return self.p._finalize(new_id, outcome)  # noqa: SLF001

    def _record_gate_stages(
        self,
        new_id: str,
        outcome: InstanceOutcome,
        sig: CoverageSignature,
        baseline: CoverageSignature,
        seen: set,
    ) -> None:
        """Add informational gate statuses; never drop a harvested candidate."""
        cov_ok, cov_detail, cov_bad = self._coverage_gate(sig, baseline, seen)
        outcome.add_stage("coverage", cov_ok, cov_detail or cov_bad)
        oracle_ok, oracle_detail, oracle_bad = self._oracle_gate(new_id, outcome, seen)
        outcome.add_stage("oracle", oracle_ok, oracle_detail or oracle_bad)

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
