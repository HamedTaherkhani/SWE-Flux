"""Result/value objects passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class InstanceClassification:
    """Whether the target model currently answers an instance correctly."""

    instance_id: str
    passing: bool
    reason: str  # "correct", a mismatch reason, or "missing_pred"/"missing_oracle"


@dataclass
class PassFailReport:
    repo: str
    classifications: List[InstanceClassification] = field(default_factory=list)

    @property
    def passing_ids(self) -> List[str]:
        return [c.instance_id for c in self.classifications if c.passing]

    @property
    def failing_ids(self) -> List[str]:
        return [c.instance_id for c in self.classifications if not c.passing]


@dataclass
class PerturbationResult:
    """Output of applying a strategy to one test's source."""

    new_source: str
    n_changes: int
    strategy: str
    seed: int


@dataclass
class StageStatus:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class InstanceOutcome:
    """End-to-end result for one (original instance, strategy, seed) attempt."""

    repo: str
    original_id: str
    new_id: str
    strategy: str
    seed: int
    question_kind: Optional[str] = None

    n_changes: int = 0
    model_passed_original: Optional[bool] = None
    model_passed_new: Optional[bool] = None
    oracle_changed: Optional[bool] = None
    model: Optional[str] = None
    # Coverage signals (populated in explore mode).
    covered_lines: Optional[int] = None
    new_lines_vs_baseline: Optional[int] = None
    new_edges_vs_baseline: Optional[int] = None
    trace_same_as_original: Optional[bool] = None
    kept: Optional[bool] = None  # explore mode: did this candidate survive the gate
    stages: List[StageStatus] = field(default_factory=list)
    notes: str = ""

    @property
    def harvested(self) -> bool:
        return any(s.name == "harvest" and s.ok for s in self.stages)

    @property
    def persisted(self) -> bool:
        """Did this attempt produce a real generated instance on disk?

        Harvest success is the retention boundary. Broken perturbations are not
        persisted, but harvested perturbations are saved even when their oracle,
        trace, or model outcome does not change.
        """
        if not self.harvested:
            return False
        return any(s.name == "relocate" and s.ok for s in self.stages)

    @property
    def flipped_to_fail(self) -> Optional[bool]:
        """True iff model answered the original correctly but the perturbed one wrong."""
        if self.model_passed_original is None or self.model_passed_new is None:
            return None
        return self.model_passed_original and not self.model_passed_new

    @property
    def same_oracle(self) -> Optional[bool]:
        if self.oracle_changed is None:
            return None
        return not self.oracle_changed

    @property
    def trace_changed(self) -> Optional[bool]:
        if self.trace_same_as_original is None:
            return None
        return not self.trace_same_as_original

    @property
    def coverage_changed(self) -> Optional[bool]:
        if self.new_lines_vs_baseline is None and self.new_edges_vs_baseline is None:
            return None
        return bool(self.new_lines_vs_baseline or self.new_edges_vs_baseline)

    @property
    def category(self) -> str:
        oracle = (
            "same-oracle" if self.same_oracle is True
            else "oracle-change" if self.same_oracle is False
            else "oracle-unknown"
        )
        trace = (
            "same-trace" if self.trace_same_as_original is True
            else "different-trace" if self.trace_same_as_original is False
            else "trace-unknown"
        )
        flip = (
            "flip" if self.flipped_to_fail is True
            else "no-flip" if self.flipped_to_fail is False
            else "flip-unknown"
        )
        return f"{oracle}__{trace}__{flip}"

    @staticmethod
    def _pass_label(value: Optional[bool]) -> str:
        if value is True:
            return "pass"
        if value is False:
            return "fail"
        return "unknown"

    def add_stage(self, name: str, ok: bool, detail: str = "") -> StageStatus:
        status = StageStatus(name=name, ok=ok, detail=detail)
        self.stages.append(status)
        return status

    def to_dict(self) -> Dict:
        model = self.model or "model"
        return {
            "repo": self.repo,
            "original_id": self.original_id,
            "new_id": self.new_id,
            "strategy": self.strategy,
            "seed": self.seed,
            "question_kind": self.question_kind,
            "n_changes": self.n_changes,
            "oracle_harvest_succeeded": self.harvested,
            "model_passed_original": self.model_passed_original,
            "model_passed_new": self.model_passed_new,
            "model_results": {
                f"{model}_original": self._pass_label(self.model_passed_original),
                f"{model}_perturbed": self._pass_label(self.model_passed_new),
            },
            "oracle_changed": self.oracle_changed,
            "same_oracle": self.same_oracle,
            "covered_lines": self.covered_lines,
            "new_lines_vs_baseline": self.new_lines_vs_baseline,
            "new_edges_vs_baseline": self.new_edges_vs_baseline,
            "trace_same_as_original": self.trace_same_as_original,
            "trace_changed": self.trace_changed,
            "gate_results": {
                "coverage": self.coverage_changed,
                "oracle_change": self.oracle_changed,
                "flip": self.flipped_to_fail,
            },
            "category": self.category,
            "kept": self.kept,
            "harvested": self.harvested,
            "flipped_to_fail": self.flipped_to_fail,
            "stages": [{"name": s.name, "ok": s.ok, "detail": s.detail} for s in self.stages],
            "notes": self.notes,
        }
