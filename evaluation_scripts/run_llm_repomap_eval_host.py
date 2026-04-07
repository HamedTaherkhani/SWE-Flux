#!/usr/bin/env python3
"""Run read-only QA evaluation on host using LLM + aider RepoMap.

This runner does not execute repository code/tests.
It uses only read-only tools exposed in `run_llm_repomap_eval_in_docker.py`.

Output layout:
  <output-root>/llm/<provider>/<model>/<repo>/<instance>/answer.json
  <output-root>/llm/<provider>/<model>/<repo>/<instance>/traj.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import run_llm_repomap_eval_in_docker as core

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_checked(cmd: List[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, capture_output=capture)


def have_docker() -> bool:
    return subprocess.run(["bash", "-lc", "command -v docker >/dev/null 2>&1"]).returncode == 0


def parse_repo_root_from_question(question_text: str) -> Optional[Path]:
    m = re.search(r"(/testbed/[A-Za-z0-9_.-]+/)", question_text or "")
    if not m:
        return None
    candidate = Path(m.group(1)).resolve()
    if candidate.exists():
        return candidate
    return None


def default_repo_candidates(repo_name: str, base: Path) -> List[Path]:
    aliases = {
        "Sympy": ["sympy", "Sympy"],
        "Keras": ["keras", "Keras"],
        "Telegram_bot": ["python-telegram-bot", "telegram_bot", "Telegram_bot"],
        "Faker": ["faker", "Faker"],
        "Xarray": ["xarray", "Xarray"],
    }
    names = aliases.get(repo_name, [repo_name, repo_name.lower()])
    return [(base / n).resolve() for n in names]


def infer_repo_subdir_from_question(repo_instances_dir: Path) -> Optional[str]:
    qfiles = sorted(repo_instances_dir.glob("*/question.json"))
    if not qfiles:
        return None
    first_q = load_json(qfiles[0])
    question = str(first_q.get("question", ""))
    m = re.search(r"(/testbed/[A-Za-z0-9_.-]+/)", question)
    if not m:
        return None
    p = Path(m.group(1))
    parts = p.parts
    # e.g. /testbed/sympy/
    if len(parts) >= 3:
        return parts[2]
    return None


def list_testbed_dirs(image: str) -> List[str]:
    proc = run_checked(
        ["docker", "run", "--rm", image, "bash", "-lc", "ls -1A /testbed"],
        capture=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def infer_repo_subdir_for_image(repo_name: str, repo_instances_dir: Path, image: str) -> str:
    from_question = infer_repo_subdir_from_question(repo_instances_dir)
    if from_question:
        return from_question

    dirs = list_testbed_dirs(image)
    aliases = [p.name for p in default_repo_candidates(repo_name, Path("/testbed"))]
    for alias in aliases:
        if alias in dirs:
            return alias

    # Some images place repository root directly at /testbed (no nested subdir).
    root_markers = {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "README.md",
        "README.rst",
        ".git",
    }
    if any(marker in dirs for marker in root_markers):
        return "."

    if len(dirs) == 1:
        return dirs[0]
    raise RuntimeError(
        f"Could not infer /testbed repo subdir for {repo_name}. Found dirs: {dirs}"
    )


def materialize_repo_snapshot(
    *,
    repo_name: str,
    image: str,
    repo_instances_dir: Path,
    mount_root: Path,
    refresh: bool,
) -> Tuple[Path, bool]:
    if not have_docker():
        raise RuntimeError("Docker is required for snapshot materialization but is not available")

    mount_root = mount_root.resolve()
    dest = mount_root / repo_name
    if dest.exists() and any(dest.iterdir()) and not refresh:
        print(f"[{repo_name}] Using existing mounted snapshot: {dest}")
        return dest, False

    if refresh and dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # Ensure image exists locally.
    if subprocess.run(["docker", "image", "inspect", image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        print(f"[{repo_name}] Pulling image for snapshot: {image}")
        run_checked(["docker", "pull", image])

    repo_subdir = infer_repo_subdir_for_image(repo_name, repo_instances_dir, image)
    container_name = f"repobehave-snap-{core.sanitize_name(repo_name).lower()}-{os.getpid()}"
    src_label = "/testbed" if repo_subdir == "." else f"/testbed/{repo_subdir}"
    print(f"[{repo_name}] Materializing {src_label} -> {dest}")

    run_checked(["docker", "create", "--name", container_name, image], capture=True)
    try:
        run_checked(["docker", "cp", f"{container_name}:/testbed/{repo_subdir}/.", str(dest)])
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not any(dest.iterdir()):
        raise RuntimeError(f"Snapshot materialization produced empty directory: {dest}")

    return dest, True


def resolve_repo_root(
    *,
    repo_name: str,
    repo_instances_dir: Path,
    explicit_repo_root: Optional[str],
    repo_roots_map: Dict[str, str],
    repo_root_base: Path,
) -> Path:
    if explicit_repo_root:
        p = Path(explicit_repo_root).resolve()
        if not p.exists():
            raise RuntimeError(f"Configured repo root does not exist: {p}")
        return p

    mapped = repo_roots_map.get(repo_name)
    if mapped:
        p = Path(mapped).resolve()
        if not p.exists():
            raise RuntimeError(f"Mapped repo root does not exist for {repo_name}: {p}")
        return p

    qfiles = sorted(repo_instances_dir.glob("*/question.json"))
    if qfiles:
        first_q = load_json(qfiles[0])
        inferred = parse_repo_root_from_question(str(first_q.get("question", "")))
        if inferred:
            return inferred

    for candidate in default_repo_candidates(repo_name, repo_root_base):
        if candidate.exists():
            return candidate

    raise RuntimeError(
        f"Could not resolve repo root for {repo_name}. "
        "Use --repo-root (single repo) or --repo-roots-file (all/multiple repos)."
    )


def run_repo(
    *,
    provider: str,
    model: str,
    repo_name: str,
    repo_root: Path,
    instances_dir: Path,
    out_repo_root: Path,
    num_instances: str,
    repomap_tokens: int,
    max_tool_rounds: int,
    max_read_lines: int,
    max_read_chars: int,
    temperature: float,
    max_repair_rounds: int,
    print_llm_trace: bool,
    resume: bool,
) -> None:
    selected_ids = core.select_instances(instances_dir, num_instances)
    if not selected_ids:
        print(f"[{repo_name}] Skipping: no instances selected")
        return

    out_repo_root.mkdir(parents=True, exist_ok=True)

    print(f"[{repo_name}] repo_root={repo_root}")
    print(f"[{repo_name}] running {len(selected_ids)} instances...")
    if resume:
        print(f"[{repo_name}] resume mode enabled: completed instances will be skipped")

    for idx, instance_id in enumerate(selected_ids, start=1):
        qpath = instances_dir / instance_id / "question.json"
        out_dir = out_repo_root / instance_id
        out_dir.mkdir(parents=True, exist_ok=True)
        answer_path = out_dir / "answer.json"
        log_path = out_dir / "llm.log"
        traj_path = out_dir / "traj.json"

        if resume and answer_path.exists() and answer_path.stat().st_size > 0:
            print(f"[{repo_name}][{idx}/{len(selected_ids)}] {instance_id} (skip: answer exists)")
            continue

        print(f"[{repo_name}][{idx}/{len(selected_ids)}] {instance_id}")
        trace_prefix = f"[{repo_name}/{instance_id}] "
        trajectory_events: List[str] = []

        def _trace(msg: str) -> None:
            trajectory_events.append(msg)
            if print_llm_trace:
                print(trace_prefix + msg)

        try:
            answer, debug = core.run_single_instance(
                provider=provider,
                model=model,
                question_path=qpath,
                repo_root=repo_root,
                repomap_tokens=repomap_tokens,
                max_tool_rounds=max_tool_rounds,
                max_read_lines=max_read_lines,
                max_read_chars=max_read_chars,
                temperature=temperature,
                max_repair_rounds=max_repair_rounds,
                trace=_trace,
            )
            core.dump_json(answer_path, answer)
            core.dump_json(
                traj_path,
                {
                    "status": "ok",
                    "instance": instance_id,
                    "events": trajectory_events,
                },
            )
            log_payload = {"status": "ok", "instance": instance_id, "debug": debug}
            # Defensive guarantee: success should always have answer.json.
            if not answer_path.exists():
                core.dump_json(answer_path, answer)
        except Exception as exc:
            core.dump_json(
                traj_path,
                {
                    "status": "error",
                    "instance": instance_id,
                    "events": trajectory_events,
                    "error": str(exc),
                },
            )
            log_payload = {
                "status": "error",
                "instance": instance_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

        log_path.write_text(json.dumps(log_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run host-side read-only LLM RepoMap QA eval")
    p.add_argument("--provider", choices=["openai", "gemini", "anthropic"], required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--repo", default="all", help="Repo name under qa_instances_eval, or all")
    p.add_argument("--instances-root", default=str(REPO_ROOT / "qa_instances_eval"))
    p.add_argument("--output-root", default=str(REPO_ROOT / "evaluations"))
    p.add_argument("--num-instances", default="all", help="'all' or integer")
    p.add_argument("--resume", action="store_true", help="Skip instances that already have non-empty answer.json")
    p.add_argument(
        "--repos-file",
        default=str(REPO_ROOT / "Repositories.json"),
        help="Repo->docker-image mapping for snapshot mount",
    )
    p.add_argument(
        "--mount-root",
        default=str(REPO_ROOT / ".tmp_mounted_repos"),
        help="Temporary mount root inside RepoBehave for materialized repos",
    )
    p.add_argument(
        "--materialize-missing-from-image",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="If repo root is missing, copy repo snapshot from docker image into --mount-root",
    )
    p.add_argument(
        "--refresh-mounted-repos",
        action="store_true",
        help="Re-copy snapshots from image even if mounted repo folder already exists",
    )
    p.add_argument(
        "--cleanup-mounted-repos",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Delete repos that were materialized into --mount-root after evaluation completes",
    )

    p.add_argument(
        "--repo-root",
        default="",
        help="Absolute/local path to mounted source repo root (valid only with single --repo)",
    )
    p.add_argument(
        "--repo-roots-file",
        default="",
        help="JSON file mapping repo name -> local mounted repo root path",
    )
    p.add_argument(
        "--repo-root-base",
        default="/testbed",
        help="Base path used for fallback repo-root discovery (default: /testbed)",
    )

    p.add_argument("--max-tool-rounds", type=int, default=24)
    p.add_argument("--repomap-tokens", type=int, default=8192)
    p.add_argument("--max-read-lines", type=int, default=300)
    p.add_argument("--max-read-chars", type=int, default=120000)
    p.add_argument("--max-repair-rounds", type=int, default=2)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument(
        "--print-llm-trace",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print full LLM/tool interaction trace to console",
    )
    return p


def main() -> int:
    if load_dotenv is not None:
        load_dotenv()

    args = build_parser().parse_args()

    if args.num_instances != "all":
        try:
            n = int(args.num_instances)
        except ValueError as exc:
            raise SystemExit("--num-instances must be 'all' or an integer") from exc
        if n < 0:
            raise SystemExit("--num-instances must be >= 0")

    instances_root = Path(args.instances_root).resolve()
    if not instances_root.exists():
        raise SystemExit(f"Instances root not found: {instances_root}")

    repo_dirs = sorted(p.name for p in instances_root.iterdir() if p.is_dir())
    if args.repo == "all":
        target_repos = repo_dirs
    else:
        if args.repo not in repo_dirs:
            raise SystemExit(f"Repo '{args.repo}' not found in {instances_root}. Available: {repo_dirs}")
        target_repos = [args.repo]

    if args.repo_root and len(target_repos) != 1:
        raise SystemExit("--repo-root can only be used with a single --repo (not all)")

    repo_roots_map: Dict[str, str] = {}
    if args.repo_roots_file:
        mapping = load_json(Path(args.repo_roots_file).resolve())
        if not isinstance(mapping, dict):
            raise SystemExit("--repo-roots-file must contain a JSON object {repo: path}")
        repo_roots_map = {str(k): str(v) for k, v in mapping.items()}

    repos_images: Dict[str, str] = {}
    if args.materialize_missing_from_image:
        repos_file = Path(args.repos_file).resolve()
        if not repos_file.exists():
            raise SystemExit(f"--repos-file not found: {repos_file}")
        data = load_json(repos_file)
        if not isinstance(data, dict):
            raise SystemExit(f"--repos-file must be a JSON object (repo->image): {repos_file}")
        repos_images = {str(k): str(v) for k, v in data.items()}

    model_segment = core.sanitize_name(args.model)
    out_model_root = Path(args.output_root).resolve() / "llm" / args.provider / model_segment
    out_model_root.mkdir(parents=True, exist_ok=True)
    mount_root = Path(args.mount_root).resolve()

    print(f"Provider:            {args.provider}")
    print(f"Model:               {args.model}")
    print(f"Output root:         {out_model_root}")
    print(f"Target repos:        {' '.join(target_repos)}")
    print(f"Instances root:      {instances_root}")
    print(f"Repo root base:      {Path(args.repo_root_base).resolve()}")
    print(f"Mount root:          {mount_root}")
    print(f"Resume mode:         {'enabled' if args.resume else 'disabled'}")
    print("Mode:                host-side read-only (no code execution)")
    print()

    mounted_to_cleanup: List[Path] = []
    try:
        for repo_name in target_repos:
            instances_dir = instances_root / repo_name
            if not instances_dir.exists():
                print(f"[{repo_name}] Skipping: missing {instances_dir}")
                continue
            explicit_repo_root = args.repo_root if len(target_repos) == 1 else ""
            mapped_repo_root = repo_roots_map.get(repo_name, "")
            default_mount_repo_root = (mount_root / repo_name).resolve()

            # Default behavior: use .tmp mount root by repo name when no explicit/mapped repo root.
            if not explicit_repo_root and not mapped_repo_root:
                if default_mount_repo_root.exists() and any(default_mount_repo_root.iterdir()):
                    repo_root = default_mount_repo_root
                    print(f"[{repo_name}] Using default mounted repo root: {repo_root}")
                elif args.materialize_missing_from_image:
                    image = repos_images.get(repo_name)
                    if not image:
                        print(f"[{repo_name}] Skipping: missing image mapping in {args.repos_file}")
                        continue
                    try:
                        repo_root, created_now = materialize_repo_snapshot(
                            repo_name=repo_name,
                            image=image,
                            repo_instances_dir=instances_dir,
                            mount_root=mount_root,
                            refresh=args.refresh_mounted_repos,
                        )
                        if created_now:
                            mounted_to_cleanup.append(repo_root)
                    except Exception as mount_exc:
                        print(f"[{repo_name}] Skipping: failed to materialize snapshot: {mount_exc}")
                        continue
                else:
                    print(
                        f"[{repo_name}] Skipping: default mounted repo root missing and materialization disabled: "
                        f"{default_mount_repo_root}"
                    )
                    continue
            else:
                try:
                    repo_root = resolve_repo_root(
                        repo_name=repo_name,
                        repo_instances_dir=instances_dir,
                        explicit_repo_root=explicit_repo_root,
                        repo_roots_map=repo_roots_map,
                        repo_root_base=Path(args.repo_root_base).resolve(),
                    )
                except Exception as exc:
                    if not args.materialize_missing_from_image:
                        print(f"[{repo_name}] Skipping: {exc}")
                        continue
                    image = repos_images.get(repo_name)
                    if not image:
                        print(f"[{repo_name}] Skipping: missing image mapping in {args.repos_file}")
                        continue
                    try:
                        repo_root, created_now = materialize_repo_snapshot(
                            repo_name=repo_name,
                            image=image,
                            repo_instances_dir=instances_dir,
                            mount_root=mount_root,
                            refresh=args.refresh_mounted_repos,
                        )
                        if created_now:
                            mounted_to_cleanup.append(repo_root)
                    except Exception as mount_exc:
                        print(f"[{repo_name}] Skipping: failed to materialize snapshot: {mount_exc}")
                        continue

            run_repo(
                provider=args.provider,
                model=args.model,
                repo_name=repo_name,
                repo_root=repo_root,
                instances_dir=instances_dir,
                out_repo_root=out_model_root / repo_name,
                num_instances=args.num_instances,
                repomap_tokens=args.repomap_tokens,
                max_tool_rounds=args.max_tool_rounds,
                max_read_lines=args.max_read_lines,
                max_read_chars=args.max_read_chars,
                temperature=args.temperature,
                max_repair_rounds=args.max_repair_rounds,
                print_llm_trace=args.print_llm_trace,
                resume=args.resume,
            )
    finally:
        if args.cleanup_mounted_repos and mounted_to_cleanup:
            print()
            print("Cleaning up materialized repo snapshots...")
            for p in mounted_to_cleanup:
                try:
                    shutil.rmtree(p)
                    print(f"- removed {p}")
                except Exception as exc:
                    print(f"- failed to remove {p}: {exc}")

    print()
    print(f"Done. Outputs at: {out_model_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
