"""Classify instances as passing/failing for a target model.

This is a thin adapter over the existing ``evaluate_qa_answers`` scorer -- we do
NOT re-implement answer comparison. We reuse its ``compare_values`` and path
helpers so "passing" here means exactly what the project's evaluator means.
"""

from __future__ import annotations

from typing import Optional

from .config import PerturbationConfig
from .models import InstanceClassification, PassFailReport
from .paths import RepoLayout, ensure_repo_on_path

ensure_repo_on_path()
from evaluation_scripts import evaluate_qa_answers as eqa  # noqa: E402


class InstanceClassifier:
    """Decides pass/fail per instance using the project's own evaluator."""

    def __init__(self, config: PerturbationConfig, layout: RepoLayout) -> None:
        self.config = config
        self.layout = layout

    def classify_instance(self, repo: str, instance_id: str) -> InstanceClassification:
        oracle_path = self.layout.oracle_path(repo, instance_id)
        pred_path = self.layout.prediction_answer(
            repo, instance_id, self.config.vendor, self.config.model, self.config.tool
        )

        if not oracle_path.exists():
            return InstanceClassification(instance_id, False, "missing_oracle")
        if not pred_path.exists():
            return InstanceClassification(instance_id, False, "missing_pred")

        try:
            oracle = eqa.load_json(oracle_path)
            pred_raw = eqa.load_json(pred_path)
        except Exception as exc:  # noqa: BLE001 - mirror evaluator's leniency
            return InstanceClassification(instance_id, False, f"invalid_json: {exc}")

        oracle_answer = oracle.get("oracle_answer") if isinstance(oracle, dict) else oracle
        pred_answer = eqa.pick_answer_payload(pred_raw)

        result = eqa.compare_values(
            expected=oracle_answer,
            pred=pred_answer,
            key_name="root",
            path="$",
            float_tol=1e-6,
        )
        return InstanceClassification(
            instance_id,
            result.ok,
            "correct" if result.ok else (result.reason or "mismatch"),
        )

    def classify_repo(self, repo: str, instance_ids: Optional[list[str]] = None) -> PassFailReport:
        ids = instance_ids if instance_ids is not None else self.layout.list_instances(repo)
        report = PassFailReport(repo=repo)
        for instance_id in ids:
            report.classifications.append(self.classify_instance(repo, instance_id))
        return report
