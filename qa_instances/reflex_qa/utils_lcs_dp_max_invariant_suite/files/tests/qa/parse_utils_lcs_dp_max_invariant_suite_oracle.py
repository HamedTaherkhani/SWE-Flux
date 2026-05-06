#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_FILE = Path("/testbed/reflex/utils/format.py")
TARGET_FUNC = "reflex.utils.format.length_of_largest_common_substring"
TARGET_LINE = 54

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
            dp = ast.literal_eval(frame["dp"])
            i = int(ast.literal_eval(frame["i"]))
            j = int(ast.literal_eval(frame["j"]))
            max_length = int(ast.literal_eval(frame["max_length"]))
            values.append((dp[i][j], max_length))
    if not values:
        raise ValueError("No target evaluations observed.")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default="/testbed/logs/qa_instances/utils_lcs_dp_max_invariant_suite/trace.log")
    parser.add_argument("--out", default="/testbed/logs/qa_instances/utils_lcs_dp_max_invariant_suite/oracle.json")
    args = parser.parse_args()
    values = extract_values(Path(args.trace_log).read_text(encoding="utf-8"))
    invariant_exists = all(current_cell >= max_length for current_cell, max_length in values)
    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in `tests/qa/utils_lcs_dp_max_invariant_suite_test.py` "
            "(all 10 test classes). Focus on `reflex/utils/format.py`, function "
            "`reflex.utils.format.length_of_largest_common_substring`, lines 30-57. At line "
            "54 (`if dp[i][j] > max_length:`), consider local variables `dp`, `i`, `j`, and "
            "`max_length` immediately before the condition executes. Across all evaluations "
            "of this line over the full suite, is the relationship `dp[i][j] >= max_length` "
            "an invariant property? Return JSON as `{\\\"invariant_exists\\\": <bool>}` where "
            "`true` means the relationship holds for every evaluation and `false` means it "
            "does not hold."
        ),
        "template_answer": {"invariant_exists": "bool"},
        "oracle_answer": {"invariant_exists": invariant_exists},
    }
    Path(args.out).write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
