#!/usr/bin/env python3
"""Embed template_answer into each qa_instances/*/oracle.json.

The template mirrors oracle_answer structure but replaces leaf values with type
labels (e.g., str, int, float, bool, null).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SKIP_DIRS = {"shared", "qa_artifacts"}


def type_label(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    return "object"


def render_type(value: Any) -> str:
    if isinstance(value, dict):
        inner = ", ".join(f"{k}: {render_type(v)}" for k, v in value.items())
        return "{" + inner + "}"
    if isinstance(value, list):
        if not value:
            return "list[object]"
        return f"list[{render_type(value[0])}]"
    return type_label(value)


def to_template(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: to_template(v) for k, v in value.items()}
    if isinstance(value, list):
        return render_type(value)
    return type_label(value)


def process_instance(instance_dir: Path, overwrite: bool) -> None:
    oracle_path = instance_dir / "oracle.json"
    if not oracle_path.exists():
        return

    with oracle_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "oracle_answer" not in data:
        return

    if "template_answer" in data and not overwrite:
        return

    data["template_answer"] = to_template(data["oracle_answer"])

    with oracle_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate template_answer.json for each qa_instances/*/oracle.json"
    )
    parser.add_argument(
        "--root",
        default="qa_instances",
        help="Root directory containing QA instances (default: qa_instances)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing template_answer in oracle.json files",
    )

    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        raise SystemExit(f"Root directory not found: {root}")

    for instance_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if instance_dir.name in SKIP_DIRS:
            continue
        process_instance(instance_dir, args.overwrite)


if __name__ == "__main__":
    main()
