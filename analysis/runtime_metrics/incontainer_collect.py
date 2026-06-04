#!/usr/bin/env python3
"""Run *inside* a repo's Docker container: stage each QA instance's test files
into the repo checkout, run them under metrics_plugin, and emit raw per-test
runtime metrics.

Output: <out> (default /tmp/metrics_raw.json) with schema
  {
    "repo": "Keras",
    "python_version": "3.10.17",
    "tests": [ {"instance": "...", "test_id": "...", "metrics": {...}}, ... ]
  }

Robustness notes:
  - Tests that raise (e.g. exception-region QA instances) still get recorded:
    the plugin writes metrics after the call phase regardless of pass/fail.
  - `--continue-on-collection-errors` keeps one bad import/id from zeroing the run.
  - Some repos reuse a generic test filename (e.g. tests/qa/testcase.py) across
    instances, so staging them together would overwrite each other. Such
    colliding instances are detected and run one at a time in isolation.

Usage (in container):
  python incontainer_collect.py --repo Keras \
      --qa-root /testbed/qa_instances --repo-root /testbed --out /tmp/metrics_raw.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = {"shared", "qa_artifacts"}
_TEST_ID_RE = re.compile(r'^\s*TEST_ID=(?:"([^"]+)"|\'([^\']+)\'|(\S+))', re.MULTILINE)


@dataclass
class Instance:
    name: str
    stage: list[tuple[Path, Path]]  # (src, dst)
    test_ids: list[str]
    test_dests: set[str] = field(default_factory=set)      # resolved test-file paths
    test_file_dsts: set[str] = field(default_factory=set)   # staged test-file paths (for map)


def test_ids_from_eval(eval_sh: Path) -> list[str]:
    """Extract the pytest node id(s) the instance's oracle actually runs."""
    if not eval_sh.is_file():
        return []
    ids: list[str] = []
    for m in _TEST_ID_RE.finditer(eval_sh.read_text(encoding="utf-8", errors="replace")):
        val = next(g for g in m.groups() if g is not None).strip()
        # Accept node ids (file::class::method) and bare test files (testcase.py).
        if ("::" in val or val.endswith(".py")) and val not in ids:
            ids.append(val)
    return ids


def skip_staging(path: Path) -> bool:
    if "__pycache__" in path.parts or path.suffix == ".pyc":
        return True
    # Skip oracle parser helpers (parse_*_oracle.py) but never real test files
    # whose names happen to start with "parse" (e.g. parse_iso8601_..._test.py).
    if path.name.startswith("parse") and path.suffix == ".py" and not path.name.endswith("_test.py"):
        return True
    return False


def stage_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def gather_instances(repo_qa: Path, repo_root: Path) -> list[Instance]:
    instances: list[Instance] = []
    for inst_dir in sorted(p for p in repo_qa.iterdir() if p.is_dir()):
        if inst_dir.name in SKIP_DIRS:
            continue
        files_root = inst_dir / "files"
        if not files_root.is_dir():
            continue

        stage = [
            (f, repo_root / f.relative_to(files_root))
            for f in sorted(files_root.rglob("*"))
            if f.is_file() and not skip_staging(f)
        ]
        name_to_dst = {dst.name: dst for _, dst in stage}

        raw_ids = test_ids_from_eval(inst_dir / "eval.sh")
        if not raw_ids:
            raw_ids = [str(tf.relative_to(files_root)) for tf in sorted(files_root.rglob("*_test.py"))]
        if not raw_ids:
            continue

        # eval.sh may reference the test file by a bare name, a repo-relative
        # path, or a full host-style path. Trust only the basename and rebuild
        # the node id from the file we actually staged.
        norm_ids: list[str] = []
        test_dests: set[str] = set()
        test_file_dsts: set[str] = set()
        for rid in raw_ids:
            parts = rid.split("::")
            basename = parts[0].replace("\\", "/").rsplit("/", 1)[-1]
            dst = name_to_dst.get(basename)
            if dst is None:
                norm_ids.append(rid)  # best effort; pytest will skip if absent
                continue
            rel = str(dst.relative_to(repo_root))
            norm_ids.append("::".join([rel, *parts[1:]]) if len(parts) > 1 else rel)
            test_dests.add(str(dst.resolve()))
            test_file_dsts.add(str(dst))

        instances.append(
            Instance(inst_dir.name, stage, norm_ids, test_dests, test_file_dsts)
        )
    return instances


def pick_python(repo_root: Path) -> str:
    """Some repos (e.g. reflex) install pytest in a project venv, not the base
    interpreter. Prefer that venv's python when present."""
    venv_py = repo_root / ".venv" / "bin" / "python"
    return str(venv_py) if venv_py.exists() else sys.executable


def run_pytest(ids: list[str], env: dict, repo_root: Path, force_instance: str | None) -> None:
    e = dict(env)
    if force_instance:
        e["METRICS_FORCE_INSTANCE"] = force_instance
    else:
        e.pop("METRICS_FORCE_INSTANCE", None)
    cmd = [
        pick_python(repo_root), "-m", "pytest",
        "-p", "metrics_plugin",
        "-p", "no:cacheprovider",
        "-q", "-rA",
        "--continue-on-collection-errors",
        *ids,
    ]
    subprocess.run(cmd, env=e, cwd=str(repo_root))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--qa-root", default="/testbed/qa_instances")
    ap.add_argument("--repo-root", default="/testbed")
    ap.add_argument("--out", default="/tmp/metrics_raw.json")
    ap.add_argument("--plugin-dir", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    repo_qa = Path(args.qa_root).resolve() / args.repo
    if not repo_qa.is_dir():
        sys.exit(f"QA repo dir not found: {repo_qa}")

    # Stage shared support files (conftest / trace plugin) if present.
    shared_files = repo_qa / "shared" / "files"
    if shared_files.is_dir():
        for f in sorted(shared_files.rglob("*")):
            if f.is_file():
                stage_file(f, repo_root / f.relative_to(shared_files))

    instances = gather_instances(repo_qa, repo_root)
    if not instances:
        sys.exit(f"No QA instances with test ids found under {repo_qa}")

    # An instance must run in isolation if any of its test files would be
    # overwritten by another instance staged to the same destination path.
    dest_counts: Counter[str] = Counter()
    for inst in instances:
        dest_counts.update(inst.test_dests)
    batch = [i for i in instances if not any(dest_counts[d] > 1 for d in i.test_dests)]
    isolated = [i for i in instances if any(dest_counts[d] > 1 for d in i.test_dests)]

    out_jsonl = "/tmp/metrics_per_test.jsonl"
    map_path = "/tmp/metrics_file_instance_map.json"
    try:
        os.remove(out_jsonl)
    except OSError:
        pass

    env = dict(os.environ)
    env["METRICS_OUT"] = out_jsonl
    env["METRICS_REPO_ROOT"] = str(repo_root)
    env["METRICS_FILE_INSTANCE_MAP"] = map_path
    env["PYTHONPATH"] = args.plugin_dir + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("TRACE_ON", None)  # ensure the legacy tracer stays off

    # Batch: stage all non-colliding instances, run one pytest session, attribute
    # each test back to its instance via the file->instance map.
    file_instance_map: dict[str, str] = {}
    batch_ids: list[str] = []
    for inst in batch:
        for src, dst in inst.stage:
            stage_file(src, dst)
        for dpath in inst.test_file_dsts:
            file_instance_map[dpath] = inst.name
        batch_ids.extend(inst.test_ids)
    with open(map_path, "w", encoding="utf-8") as fh:
        json.dump(file_instance_map, fh)
    if batch_ids:
        print(f"Batch: {len(batch)} instances, {len(batch_ids)} test ids", flush=True)
        run_pytest(batch_ids, env, repo_root, force_instance=None)

    # Isolated: re-stage and run each colliding instance on its own.
    for inst in isolated:
        for src, dst in inst.stage:
            stage_file(src, dst)
        print(f"Isolated: {inst.name} ({len(inst.test_ids)} test ids)", flush=True)
        run_pytest(inst.test_ids, env, repo_root, force_instance=inst.name)

    tests = []
    if os.path.exists(out_jsonl):
        with open(out_jsonl, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    tests.append(json.loads(line))

    result = {
        "repo": args.repo,
        "python_version": platform.python_version(),
        "tests": tests,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"Wrote {len(tests)} test records to {args.out}", flush=True)


if __name__ == "__main__":
    main()
