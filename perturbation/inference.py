"""Inference adapter.

Wraps the existing host LLM runner (``run_llm_repomap_eval_host.py``) for a
single perturbed instance via its ``--task-ids <repo>/<id>`` selector. We do not
re-implement model inference; we shell out so provider handling, repo-map tools,
snapshot materialization, etc. stay in one place.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass

from .config import PerturbationConfig
from .paths import DataLayout, RepoLayout


@dataclass
class InferenceResult:
    ok: bool
    returncode: int
    detail: str


class InferenceRunner:
    """Runs the LLM runner (from the source checkout) but reads questions from
    and writes predictions into the generated ``data`` layout."""

    def __init__(self, config: PerturbationConfig, tooling: RepoLayout, data: DataLayout) -> None:
        self.config = config
        self.tooling = tooling
        self.data = data

    def _python_prefix(self) -> list[str]:
        """Command prefix that launches the runner in the right environment.

        Prefers an explicit interpreter, then a conda env (via ``conda run``),
        and finally the current interpreter.
        """
        if self.config.inference_python:
            return [self.config.inference_python]
        if self.config.inference_conda_env:
            return ["conda", "run", "--no-capture-output", "-n", self.config.inference_conda_env, "python"]
        return [sys.executable]

    def run(self, repo: str, instance_id: str) -> InferenceResult:
        runner = self.tooling.inference_runner()
        if not runner.exists():
            return InferenceResult(False, -1, f"missing inference runner: {runner}")

        cmd = self._python_prefix() + [
            str(runner),
            "--provider", self.config.vendor,
            "--model", self.config.model,
            "--task-ids", f"{repo}/{instance_id}",
            "--instances-root", str(self.data.eval_root),
            "--output-root", str(self.data.evaluations_root),
            *self.config.inference_extra_args,
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.tooling.repo_root),
                capture_output=True,
                text=True,
                timeout=self.config.inference_timeout,
            )
        except subprocess.TimeoutExpired:
            return InferenceResult(False, -1, "inference timed out")

        answer = self.data.prediction_answer(
            repo, instance_id, self.config.vendor, self.config.model, self.config.tool
        )
        if proc.returncode != 0 or not answer.exists():
            detail = self._failure_detail(repo, instance_id) or (proc.stderr or proc.stdout or "")[-400:]
            return InferenceResult(False, proc.returncode, f"inference failed: {detail}")
        return InferenceResult(True, 0, "ok")

    def _failure_detail(self, repo: str, instance_id: str) -> str:
        """Prefer the runner's own error (usage.json) over noisy stdout banners."""
        usage = self.data.prediction_dir(
            repo, instance_id, self.config.vendor, self.config.model, self.config.tool
        ) / "usage.json"
        if usage.exists():
            try:
                data = json.loads(usage.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("error"):
                    return str(data["error"])
            except Exception:  # noqa: BLE001
                pass
        return ""
