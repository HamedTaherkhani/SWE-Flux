from __future__ import annotations

import json
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


def count_question_kinds(root: str | Path = "qa_instances/Keras") -> Counter[str]:
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
    _print_counts(count_question_kinds())
