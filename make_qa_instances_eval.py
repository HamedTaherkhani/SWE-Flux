#!/usr/bin/env python3
"""Build a minimal qa_instances_eval dataset for evaluation only.

For each repository under qa_instances/ (e.g. Keras, Telegram_bot, Sympy),
it creates matching repository folders in qa_instances_eval/.
For each QA instance under that repository, it creates:
- question.json (oracle.json with oracle_answer removed)
- files/ with only the instance's test cases and related files

Excluded instance-level directories:
- oracle_answer
- eval.sh
- parser scripts (parse_*.py)
- __pycache__ and .pyc files
- shared and qa_artifacts
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


SKIP_DIRS = {"shared", "qa_artifacts"}


def is_parser_file(path: Path) -> bool:
    return path.name.startswith("parse_") and path.suffix == ".py"


def should_copy_file(path: Path) -> bool:
    if "__pycache__" in path.parts:
        return False
    if path.suffix == ".pyc":
        return False
    if is_parser_file(path):
        return False
    return True


def write_question_json(src_oracle: Path, dst_question: Path) -> None:
    with src_oracle.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop("oracle_answer", None)
    dst_question.parent.mkdir(parents=True, exist_ok=True)
    with dst_question.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def copy_instance_files(src_files: Path, dst_files: Path) -> None:
    if not src_files.exists():
        return
    for path in src_files.rglob("*"):
        if not path.is_file():
            continue
        if not should_copy_file(path):
            continue
        rel = path.relative_to(src_files)
        out_path = dst_files / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out_path)


def iter_repo_instances(src_root: Path):
    for repo_dir in sorted(p for p in src_root.iterdir() if p.is_dir()):
        if repo_dir.name in SKIP_DIRS:
            continue
        for instance_dir in sorted(p for p in repo_dir.iterdir() if p.is_dir()):
            if instance_dir.name in SKIP_DIRS:
                continue
            if (instance_dir / "oracle.json").exists():
                yield repo_dir.name, instance_dir


def build_eval_instances(src_root: Path, dst_root: Path, overwrite: bool) -> None:
    if dst_root.exists():
        if not overwrite:
            raise SystemExit(
                f"Destination {dst_root} already exists. Use --overwrite to replace it."
            )
        shutil.rmtree(dst_root)

    dst_root.mkdir(parents=True, exist_ok=True)

    copied = 0
    for repo_name, instance_dir in iter_repo_instances(src_root):
        oracle_path = instance_dir / "oracle.json"
        out_instance = dst_root / repo_name / instance_dir.name
        out_instance.mkdir(parents=True, exist_ok=True)

        write_question_json(oracle_path, out_instance / "question.json")
        copy_instance_files(instance_dir / "files", out_instance / "files")
        copied += 1

    if copied == 0:
        raise SystemExit(f"No QA instances with oracle.json found under repositories in {src_root}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create qa_instances_eval with questions and test files only."
    )
    parser.add_argument(
        "--src",
        default="qa_instances",
        help="Source qa_instances directory (default: qa_instances)",
    )
    parser.add_argument(
        "--dst",
        default="qa_instances_eval",
        help="Destination directory (default: qa_instances_eval)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace destination directory if it exists",
    )

    args = parser.parse_args()
    src_root = Path(args.src).resolve()
    dst_root = Path(args.dst).resolve()

    if not src_root.exists():
        raise SystemExit(f"Source directory not found: {src_root}")

    build_eval_instances(src_root, dst_root, args.overwrite)


if __name__ == "__main__":
    main()
