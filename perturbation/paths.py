"""Filesystem layout helpers for the RepoBehave benchmark.

Two layout flavours keep *source* (the real benchmark + its tooling) cleanly
separated from *generated* (perturbed) artifacts:

* :class:`RepoLayout` -- the real checkout: original instances, the harvesting
  scripts, the inference runner, and the existing predictions.
* :class:`OutputLayout` -- a self-contained mirror (default
  ``perturbation/generated/``) where new perturbed instances and their
  evaluations are stored, so the main benchmark trees stay untouched.

Both share the data-path API via :class:`DataLayout`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# RepoBehave checkout root: <root>/perturbation/paths.py -> parents[1]
REPO_ROOT = Path(__file__).resolve().parents[1]

# Default home for generated (perturbed) artifacts.
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "perturbation" / "generated"

# Default home for temporary repo source snapshots materialized from eval images.
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "perturbation" / ".tmp_mounted_repos"


def ensure_repo_on_path() -> None:
    """Make the repo root and ``evaluation_scripts`` importable.

    We reuse the existing evaluation/dataset modules instead of duplicating
    their logic, so they must be importable as packages/modules.
    """
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


class DataLayout:
    """Resolves *data* paths (instances / questions / predictions) under a root.

    Mirrors the benchmark conventions:

    * oracle instances  -> ``<root>/qa_instances/<repo>/<id>/``
    * eval question set -> ``<root>/qa_instances_eval/<repo>/<id>/``
    * predictions       -> ``<root>/evaluations/llm/<vendor>/<model>/<repo>/<id>/``
    """

    def __init__(
        self,
        root: Path | str,
        *,
        qa_dirname: str = "qa_instances",
        eval_dirname: str = "qa_instances_eval",
        evaluations_dirname: str = "evaluations",
    ) -> None:
        self.root = Path(root).resolve()
        self.qa_root = self.root / qa_dirname
        self.eval_root = self.root / eval_dirname
        self.evaluations_root = self.root / evaluations_dirname

    # -- oracle (qa_instances) -------------------------------------------------
    def repo_qa_dir(self, repo: str) -> Path:
        return self.qa_root / repo

    def qa_instance_dir(self, repo: str, instance_id: str) -> Path:
        return self.repo_qa_dir(repo) / instance_id

    def oracle_path(self, repo: str, instance_id: str) -> Path:
        return self.qa_instance_dir(repo, instance_id) / "oracle.json"

    # -- eval question set (qa_instances_eval) ---------------------------------
    def eval_instance_dir(self, repo: str, instance_id: str) -> Path:
        return self.eval_root / repo / instance_id

    # -- predictions (evaluations) ---------------------------------------------
    def prediction_dir(self, repo: str, instance_id: str, vendor: str, model: str, tool: str = "llm") -> Path:
        if tool.lower() == "llm":
            return self.evaluations_root / "llm" / vendor.lower() / model / repo / instance_id
        return self.evaluations_root / tool / model / repo / instance_id

    def prediction_answer(self, repo: str, instance_id: str, vendor: str, model: str, tool: str = "llm") -> Path:
        return self.prediction_dir(repo, instance_id, vendor, model, tool) / "answer.json"

    def list_instances(self, repo: str, skip: Optional[set[str]] = None) -> list[str]:
        """All oracle instance ids for a repo (directories with oracle.json)."""
        skip = skip or {"shared", "qa_artifacts"}
        repo_dir = self.repo_qa_dir(repo)
        if not repo_dir.exists():
            return []
        out = []
        for child in sorted(repo_dir.iterdir()):
            if not child.is_dir() or child.name in skip:
                continue
            if (child / "oracle.json").exists():
                out.append(child.name)
        return out


class RepoLayout(DataLayout):
    """The real checkout: data + harvesting/inference tooling."""

    def __init__(self, repo_root: Path | str = REPO_ROOT, **kwargs) -> None:
        super().__init__(repo_root, **kwargs)
        self.repo_root = self.root

    def eval_script(self, repo: str, instance_id: str) -> Path:
        return self.qa_instance_dir(repo, instance_id) / "eval.sh"

    def run_qa_script(self, repo: str) -> Path:
        return self.repo_qa_dir(repo) / "run_qa_fromhost.sh"

    def harvested_oracle(self, repo: str, instance_id: str) -> Path:
        """Where ``run_qa_fromhost.sh`` drops the harvested oracle."""
        return self.repo_qa_dir(repo) / "qa_artifacts" / instance_id / "oracle.json"

    def harvest_artifacts_dir(self, repo: str, instance_id: str) -> Path:
        return self.repo_qa_dir(repo) / "qa_artifacts" / instance_id

    def inference_runner(self) -> Path:
        return self.repo_root / "evaluation_scripts" / "llm_eval" / "run_llm_repomap_eval_host.py"


class OutputLayout(DataLayout):
    """Self-contained home for generated (perturbed) artifacts."""

    def __init__(self, root: Path | str = DEFAULT_OUTPUT_ROOT, **kwargs) -> None:
        super().__init__(root, **kwargs)
