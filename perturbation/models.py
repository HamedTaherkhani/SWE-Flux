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

    n_changes: int = 0
    model_passed_original: Optional[bool] = None
    model_passed_new: Optional[bool] = None
    oracle_changed: Optional[bool] = None
    # Coverage signals (populated in explore mode).
    covered_lines: Optional[int] = None
    new_lines_vs_baseline: Optional[int] = None
    new_edges_vs_baseline: Optional[int] = None
    kept: Optional[bool] = None  # explore mode: did this candidate survive the gate
    stages: List[StageStatus] = field(default_factory=list)
    notes: str = ""

    @property
    def harvested(self) -> bool:
        return any(s.name == "harvest" and s.ok for s in self.stages)

    @property
    def persisted(self) -> bool:
        """Did this attempt produce a real, kept instance on disk?

        Broken perturbations (harvest failed) and explore drops (removed from
        disk) are not persisted -- they are excluded from reported output.
        """
        if not self.harvested:
            return False
        return self.kept is None or self.kept

    @property
    def flipped_to_fail(self) -> Optional[bool]:
        """True iff model answered the original correctly but the perturbed one wrong."""
        if self.model_passed_original is None or self.model_passed_new is None:
            return None
        return self.model_passed_original and not self.model_passed_new

    def add_stage(self, name: str, ok: bool, detail: str = "") -> StageStatus:
        status = StageStatus(name=name, ok=ok, detail=detail)
        self.stages.append(status)
        return status

    def to_dict(self) -> Dict:
        return {
            "repo": self.repo,
            "original_id": self.original_id,
            "new_id": self.new_id,
            "strategy": self.strategy,
            "seed": self.seed,
            "n_changes": self.n_changes,
            "model_passed_original": self.model_passed_original,
            "model_passed_new": self.model_passed_new,
            "oracle_changed": self.oracle_changed,
            "covered_lines": self.covered_lines,
            "new_lines_vs_baseline": self.new_lines_vs_baseline,
            "new_edges_vs_baseline": self.new_edges_vs_baseline,
            "kept": self.kept,
            "harvested": self.harvested,
            "flipped_to_fail": self.flipped_to_fail,
            "stages": [{"name": s.name, "ok": s.ok, "detail": s.detail} for s in self.stages],
            "notes": self.notes,
        }
