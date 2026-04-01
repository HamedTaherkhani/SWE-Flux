#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _start_line(source_text: str) -> int:
    tree = ast.parse(source_text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "maybe_promote":
            return node.lineno
    raise ValueError("maybe_promote not found.")


def extract_path_determinism(trace_text: str, source_text: str) -> dict[str, object]:
    _start_line(source_text)  # structural sanity check
    sequences: list[list[int]] = []
    current: list[int] = []
    in_call = False
    maybe_events: list[int] = []

    for m in LINE_RE.finditer(trace_text):
        if m.group("func").endswith(".maybe_promote"):
            maybe_events.append(int(m.group("lineno")))

    if not maybe_events:
        raise ValueError("No maybe_promote events found in trace.")
    start = min(maybe_events)

    for lineno in maybe_events:
        if lineno == start:
            if in_call and current:
                sequences.append(current)
            current = [lineno]
            in_call = True
        elif in_call:
            current.append(lineno)

    if in_call and current:
        sequences.append(current)

    if len(sequences) < 5:
        raise ValueError(f"Expected >=5 maybe_promote call paths, got {len(sequences)}.")

    first_five = sequences[:5]
    deterministic = all(path == first_five[0] for path in first_five)
    return {
        "function": "maybe_promote",
        "repetitions": 5,
        "is_line_path_identical_every_time": deterministic,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/maybe_promote_path_repeatability_hard/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/dtypes.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/maybe_promote_path_repeatability_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_path_determinism(trace_text, source_text)

    qa = {
        "question_kind": "determinism_flakiness",
        "question": (
            "Use `xarray/tests/qa/maybe_promote_path_repeatability_hard_test.py`, class "
            "`TestMaybePromotePathRepeatabilityHardQA`, and execute the full suite in that file "
            "(both test methods). In that suite, "
            "`xarray/core/dtypes.py::maybe_promote` is executed 5 times with identical input. "
            "Do the repeated runs always follow the exact same sequence of executed line numbers "
            "inside `maybe_promote`?"
        ),
        "template_answer": {
            "function": "str",
            "repetitions": "int",
            "is_line_path_identical_every_time": "bool",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
