"""Build the ``qa_instances_eval`` entry for a perturbed instance.

Reuses ``make_qa_instances_eval`` so the question.json / files layout is produced
exactly the same way as the rest of the benchmark (oracle minus oracle_answer,
test files only, parser scripts excluded).
"""

from __future__ import annotations

import shutil

from .config import PerturbationConfig
from .paths import RepoLayout, ensure_repo_on_path

ensure_repo_on_path()
import make_qa_instances_eval as mkeval  # noqa: E402


class EvalDatasetBuilder:
    def __init__(self, config: PerturbationConfig, layout: RepoLayout) -> None:
        self.config = config
        self.layout = layout

    def build(self, repo: str, instance_id: str) -> None:
        instance_dir = self.layout.qa_instance_dir(repo, instance_id)
        oracle_path = instance_dir / "oracle.json"
        if not oracle_path.exists():
            raise FileNotFoundError(f"Cannot build eval entry without oracle: {oracle_path}")

        out_dir = self.layout.eval_instance_dir(repo, instance_id)
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        mkeval.write_question_json(oracle_path, out_dir / "question.json")
        mkeval.copy_instance_files(instance_dir / "files", out_dir / "files")
