"""Create a fresh perturbed instance from an existing one.

The new instance is a sibling directory under ``qa_instances/<repo>/`` so the
existing harvesting pipeline (``run_qa_fromhost.sh`` -> ``qa_pipeline.sh`` ->
``eval.sh``) can pick it up unchanged. We keep the test file name, class and
method identical (so the question text and ``parse_*_oracle.py`` extraction logic
still match); only the directory name, the test *inputs* and the harvested
oracle differ.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import PerturbationConfig
from .paths import DataLayout, RepoLayout

_INSTANCE_ID_RE = re.compile(r'^(INSTANCE_ID=")([^"]*)(")', re.MULTILINE)
_TEST_ID_RE = re.compile(r'^TEST_ID="([^"]+)"', re.MULTILINE)

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "qa_artifacts")


@dataclass
class MaterializedInstance:
    repo: str
    new_id: str
    instance_dir: Path
    test_file: Path
    original_source: str


class InstanceMaterializer:
    """Copies an instance and rewrites it for a new perturbed id."""

    def __init__(self, config: PerturbationConfig, layout: RepoLayout) -> None:
        self.config = config
        self.layout = layout

    def _test_rel_path(self, eval_sh_text: str) -> str:
        match = _TEST_ID_RE.search(eval_sh_text)
        if not match:
            raise ValueError("Could not find TEST_ID in eval.sh")
        # TEST_ID = "<rel/path/to/test.py>::Class::method"
        return match.group(1).split("::", 1)[0]

    def materialize(self, repo: str, original_id: str, new_id: str) -> MaterializedInstance:
        src = self.layout.qa_instance_dir(repo, original_id)
        dst = self.layout.qa_instance_dir(repo, new_id)
        if not src.exists():
            raise FileNotFoundError(f"Original instance not found: {src}")
        if dst.exists():
            if not self.config.overwrite_existing:
                raise FileExistsError(f"Target instance already exists: {dst} (use overwrite)")
            shutil.rmtree(dst)

        shutil.copytree(src, dst, ignore=_IGNORE)

        # Fresh oracle will be re-harvested; drop the inherited one.
        stale_oracle = dst / "oracle.json"
        if stale_oracle.exists():
            stale_oracle.unlink()

        eval_sh = dst / "eval.sh"
        eval_text = eval_sh.read_text(encoding="utf-8")
        test_rel = self._test_rel_path(eval_text)

        # Point log/output paths at the new instance id; keep TEST_ID unchanged.
        new_eval_text, n = _INSTANCE_ID_RE.subn(rf'\g<1>{new_id}\g<3>', eval_text)
        if n == 0:
            raise ValueError("Could not rewrite INSTANCE_ID in eval.sh")
        eval_sh.write_text(new_eval_text, encoding="utf-8")

        test_file = dst / "files" / test_rel
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found in materialized instance: {test_file}")

        return MaterializedInstance(
            repo=repo,
            new_id=new_id,
            instance_dir=dst,
            test_file=test_file,
            original_source=test_file.read_text(encoding="utf-8"),
        )

    def write_perturbed_source(self, materialized: MaterializedInstance, source: str) -> None:
        materialized.test_file.write_text(source, encoding="utf-8")

    def remove(self, repo: str, new_id: str) -> None:
        """Delete a materialized instance (used to roll back failed attempts)."""
        dst = self.layout.qa_instance_dir(repo, new_id)
        if dst.exists():
            shutil.rmtree(dst)
        artifacts = self.layout.harvest_artifacts_dir(repo, new_id)
        if artifacts.exists():
            shutil.rmtree(artifacts)

    def relocate(self, repo: str, new_id: str, output: DataLayout) -> Path:
        """Move a harvested instance out of the source tree into ``output``.

        Harvesting requires the instance to live under ``qa_instances/<repo>/``;
        once a fresh oracle exists we move the whole instance into the generated
        output tree so the main benchmark stays untouched. Leftover harvest
        staging under ``qa_artifacts/`` is cleaned up.
        """
        src = self.layout.qa_instance_dir(repo, new_id)
        dst = output.qa_instance_dir(repo, new_id)
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

        artifacts = self.layout.harvest_artifacts_dir(repo, new_id)
        if artifacts.exists():
            shutil.rmtree(artifacts)
        return dst
