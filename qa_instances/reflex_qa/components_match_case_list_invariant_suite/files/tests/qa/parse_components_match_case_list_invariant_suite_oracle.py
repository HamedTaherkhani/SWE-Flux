#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_FILE = Path("/testbed/reflex/components/core/match.py")
TARGET_FUNC = "reflex.components.core.match.Match._process_match_cases"
TARGET_LINE = 160

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


def extract_values(trace_text: str) -> list[tuple[int, int]]:
    values: list[tuple[int, int]] = []
    frames: list[dict[str, str]] = []
    for match in TRACE_RE.finditer(trace_text):
        if match.group("path") != str(TARGET_FILE) or match.group("func") != TARGET_FUNC:
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
        if int(match.group("lineno")) == TARGET_LINE:
            frame = frames[-1]
            case = ast.literal_eval(frame["case"])
            case_list_repr = frame["case_list"]
            case_list_len = 0 if case_list_repr == "[]" else case_list_repr.count("_js_expr=")
            values.append((case_list_len, len(case)))
    if not values:
        raise ValueError("No target evaluations observed.")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default="/testbed/logs/qa_instances/components_match_case_list_invariant_suite/trace.log")
    parser.add_argument("--out", default="/testbed/logs/qa_instances/components_match_case_list_invariant_suite/oracle.json")
    args = parser.parse_args()
    values = extract_values(Path(args.trace_log).read_text(encoding="utf-8"))
    invariant_exists = all(case_list_len == len_case - 1 for case_list_len, len_case in values)
    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in `tests/qa/components_match_case_list_invariant_suite_test.py` "
            "(all 10 test classes). Focus on `reflex/components/core/match.py`, class method "
            "`reflex.components.core.match.Match._process_match_cases`, lines 126-164. At line "
            "160 (`case_list.append(el)`), consider local variables `case_list` and `case` "
            "immediately before the append executes. Across all evaluations of this line over "
            "the full suite, is the relationship `len(case_list) == len(case) - 1` an invariant "
            "property? Return JSON as `{\\\"invariant_exists\\\": <bool>}` where `true` means "
            "the relationship holds for every evaluation and `false` means it does not hold."
        ),
        "template_answer": {"invariant_exists": "bool"},
        "oracle_answer": {"invariant_exists": invariant_exists},
    }
    Path(args.out).write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
