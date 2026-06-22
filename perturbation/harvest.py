"""Oracle harvesting adapter.

Wraps the existing ``run_qa_fromhost.sh`` (which spins up the repo's evaluation
container, stages instrumentation, runs the instance and parses the trace into
``oracle.json``). We do not re-implement harvesting; we just invoke it and copy
the resulting oracle next to the instance so the rest of the toolchain finds it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import PerturbationConfig
from .paths import RepoLayout, ensure_repo_on_path

ensure_repo_on_path()
from make_template_answers import to_template  # noqa: E402  (reuse existing generator)


def _embed_template_answer(oracle_path: Path) -> None:
    """Add a ``template_answer`` (schema) derived from ``oracle_answer``.

    Reuses ``make_template_answers.to_template`` so generated oracles carry the
    same answer schema as the original benchmark. The schema flows into the eval
    ``question.json`` (built from the oracle), telling the model the exact output
    shape and avoiding spurious format mismatches at scoring time.
    """
    try:
        data = json.loads(oracle_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(data, dict) or "oracle_answer" not in data:
        return
    if "template_answer" in data:
        return
    data["template_answer"] = to_template(data["oracle_answer"])
    oracle_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@dataclass
class HarvestResult:
    ok: bool
    oracle_path: Optional[Path]
    returncode: int
    detail: str
    trace_path: Optional[Path] = None  # preserved trace.log for coverage analysis


class OracleHarvester:
    def __init__(self, config: PerturbationConfig, layout: RepoLayout) -> None:
        self.config = config
        self.layout = layout

    def harvest(self, repo: str, instance_id: str) -> HarvestResult:
        repo_dir = self.layout.repo_qa_dir(repo)
        script = self.layout.run_qa_script(repo)
        if not script.exists():
            return HarvestResult(False, None, -1, f"missing run_qa_fromhost.sh: {script}")

        env = os.environ.copy()
        if self.config.image:
            env["IMAGE"] = self.config.image

        try:
            proc = subprocess.run(
                ["bash", script.name, instance_id],
                cwd=str(repo_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.config.harvest_timeout,
            )
        except subprocess.TimeoutExpired:
            return HarvestResult(False, None, -1, "harvest timed out")

        harvested = self.layout.harvested_oracle(repo, instance_id)
        dest = self.layout.oracle_path(repo, instance_id)

        if proc.returncode != 0 or not harvested.exists():
            tail = (proc.stderr or proc.stdout or "")[-600:]
            return HarvestResult(False, None, proc.returncode, f"harvest failed: {tail}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(harvested, dest)
        _embed_template_answer(dest)

        # Preserve the execution trace next to the instance so it survives the
        # relocate step and can be read for coverage analysis.
        trace_dest: Optional[Path] = None
        harvested_trace = self.layout.harvest_artifacts_dir(repo, instance_id) / "trace.log"
        if harvested_trace.exists():
            trace_dest = dest.parent / "trace.log"
            shutil.copy2(harvested_trace, trace_dest)

        return HarvestResult(True, dest, 0, "ok", trace_path=trace_dest)
