from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


def _iter_question_kinds(obj: object) -> Iterable[str]:
    if isinstance(obj, dict):
        kind = obj.get("question_kind")
        if isinstance(kind, str):
            yield kind
        # Some files may nest questions under other keys; only traverse containers.
        for value in obj.values():
            yield from _iter_question_kinds(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_question_kinds(item)


def count_question_kinds(root: str | Path) -> Counter[str]:
    root_path = Path(root)
    counter: Counter[str] = Counter()

    for oracle_path in root_path.rglob("oracle.json"):
        if "qa_artifacts" in oracle_path.parts:
            continue
        try:
            payload = json.loads(oracle_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        counter.update(_iter_question_kinds(payload))

    return counter


def _print_counts(counter: Counter[str]) -> None:
    if not counter:
        print("No question_kind values found.")
        return

    width = max(len(k) for k in counter)
    total = 0
    for kind, count in counter.most_common():
        print(f"{kind:<{width}}  {count}")
        total += count
    print(f"{'TOTAL':<{width}}  {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count question_kind values in oracle.json files."
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default="Keras",
        help="Repo name under qa_instances or 'all' (default: Keras).",
    )
    args = parser.parse_args()

    base_dir = Path("qa_instances")
    if args.repo == "all":
        if not base_dir.exists():
            print("qa_instances directory not found.", file=sys.stderr)
            sys.exit(1)

        grand_total: Counter[str] = Counter()
        for repo_dir in sorted(p for p in base_dir.iterdir() if p.is_dir()):
            counter = count_question_kinds(repo_dir)
            print(f"== {repo_dir.name} ==")
            _print_counts(counter)
            print()
            grand_total.update(counter)

        if grand_total:
            print("== ALL REPOS ==")
            _print_counts(grand_total)
        else:
            print("No question_kind values found.")
        sys.exit(0)

    target_dir = base_dir / args.repo
    if not target_dir.exists():
        print(f"Repo not found: {target_dir}", file=sys.stderr)
        sys.exit(1)

    _print_counts(count_question_kinds(target_dir))
