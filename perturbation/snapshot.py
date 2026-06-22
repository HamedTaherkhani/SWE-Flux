"""Materialize a repo's source snapshot from its evaluation Docker image.

The boundary strategies are most effective when they can read the *function under
test* and straddle its real comparison constants. That source lives inside the
repo's eval image at ``/testbed``. We reuse the project's existing
``materialize_repo_snapshot`` helper (which ``docker create`` + ``docker cp``s
``/testbed`` out, no container run) to extract it into
``perturbation/.tmp_mounted_repos/<repo>/``, and remove it when done.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from .config import PerturbationConfig
from .paths import DEFAULT_SNAPSHOT_ROOT, RepoLayout, ensure_repo_on_path

ensure_repo_on_path()
from evaluation_scripts import evaluate_qa_answers as _eqa  # noqa: E402  (load_json helper)
from evaluation_scripts.llm_eval.container_runtime import build_container_runtime  # noqa: E402
from evaluation_scripts.llm_eval.run_llm_repomap_eval_host import (  # noqa: E402
    materialize_repo_snapshot,
)


class RepoSnapshotManager:
    """Extracts and cleans up repo source snapshots, reusing the eval tooling."""

    def __init__(self, config: PerturbationConfig, source: RepoLayout) -> None:
        self.config = config
        self.source = source
        self.root = Path(config.snapshot_root or DEFAULT_SNAPSHOT_ROOT)

    def image_for(self, repo: str) -> Optional[str]:
        """Resolve the eval image: explicit override, else Repositories.json."""
        if self.config.image:
            return self.config.image
        repos_file = self.source.repo_root / "Repositories.json"
        try:
            images = _eqa.load_json(repos_file)
        except Exception:  # noqa: BLE001
            return None
        return images.get(repo) if isinstance(images, dict) else None

    def snapshot_dir(self, repo: str) -> Path:
        return self.root / repo

    def materialize(self, repo: str) -> Optional[Path]:
        """Extract ``/testbed`` from the eval image into the snapshot dir.

        Returns the snapshot path, or ``None`` if Docker/the image is unavailable
        (callers then fall back to test-file thresholds only).
        """
        image = self.image_for(repo)
        if not image:
            print(f"[snapshot] no image mapping for {repo}; skipping source thresholds")
            return None

        try:
            runtime = build_container_runtime("docker")
            dest, _created = materialize_repo_snapshot(
                repo_name=repo,
                image=image,
                repo_instances_dir=self.source.eval_root / repo,
                mount_root=self.root,
                refresh=True,
                container_runtime=runtime,
            )
            return dest
        except Exception as exc:  # noqa: BLE001
            print(f"[snapshot] materialization failed for {repo}: {exc}")
            return None

    def cleanup(self, repo: str) -> None:
        dest = self.snapshot_dir(repo)
        if dest.exists():
            shutil.rmtree(dest)
            print(f"[snapshot] removed {dest}")
