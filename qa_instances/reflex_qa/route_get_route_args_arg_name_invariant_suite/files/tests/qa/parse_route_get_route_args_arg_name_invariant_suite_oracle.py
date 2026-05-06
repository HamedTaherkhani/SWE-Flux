#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_FILE = Path("/testbed/reflex/route.py")
TARGET_FUNC_PREFIX = "reflex.route.get_route_args"
TARGET_LINE = 50

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/reflex/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) (?P<rest>.*)$",
    re.MULTILINE,
)


def parse_locals(rest: str) -> dict[str, str]:
    if "locals=" not in rest:
        return {}
    try:
        parsed = ast.literal_eval(rest.split("locals=", 1)[1])
    except (SyntaxError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def extract_values(trace_text: str) -> list[tuple[str, int]]:
    values: list[tuple[str, int]] = []
    frames: list[dict[str, str]] = []
    for match in TRACE_RE.finditer(trace_text):
        if match.group("path") != str(TARGET_FILE):
            continue
        func = match.group("func")
        if not (func == TARGET_FUNC_PREFIX or func.startswith(f"{TARGET_FUNC_PREFIX}.")):
            continue
        event = match.group("event")
        locals_delta = parse_locals(match.group("rest"))
        if event == "call":
            frames.append(dict(locals_delta))
            continue
        if not frames:
            continue
        if event in {"return", "exception"}:
            frames.pop()
            continue
        frames[-1].update(locals_delta)
        if int(match.group("lineno")) == TARGET_LINE and func.endswith(".add_route_arg"):
            arg_name = ast.literal_eval(frames[-1]["arg_name"])
            args = ast.literal_eval(frames[-1]["args"])
            values.append((arg_name, len(args)))
    if not values:
        raise ValueError("No target evaluations observed.")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default="/testbed/logs/qa_instances/route_get_route_args_arg_name_invariant_suite/trace.log")
    parser.add_argument("--out", default="/testbed/logs/qa_instances/route_get_route_args_arg_name_invariant_suite/oracle.json")
    args = parser.parse_args()
    values = extract_values(Path(args.trace_log).read_text(encoding="utf-8"))
    invariant_exists = all(len(arg_name) > args_len for arg_name, args_len in values)
    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in `tests/qa/route_get_route_args_arg_name_invariant_suite_test.py` "
            "(all 10 test classes). Focus on `reflex/route.py`, function "
            "`reflex.route.get_route_args`, including nested helper `add_route_arg`, lines 28-77. "
            "At line 50 (`if arg_name in args:`), consider local variable `arg_name` and closure "
            "variable `args` in the current `add_route_arg` frame immediately before the condition "
            "executes. Across all evaluations of this line over the full suite, is the relationship "
            "`len(arg_name) > len(args)` an invariant property? Return JSON as "
            "`{\\\"invariant_exists\\\": <bool>}` where `true` means the relationship holds for every "
            "evaluation and `false` means it does not hold."
        ),
        "template_answer": {"invariant_exists": "bool"},
        "oracle_answer": {"invariant_exists": invariant_exists},
    }
    Path(args.out).write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
