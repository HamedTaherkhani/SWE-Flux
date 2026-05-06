#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dis
import json
import re
from pathlib import Path

from reflex.vars.sequence import LiteralStringVar


TARGET_PATH = Path("/testbed/reflex/vars/sequence.py")
TARGET_FUNC = "reflex.vars.sequence.LiteralStringVar.create"
INSTANCE_ID = "vars_literal_string_create_line_coverage_suite"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/reflex/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
)


def executable_lines() -> list[int]:
    """Return bytecode-reachable source lines for the exact target method."""
    code = LiteralStringVar.create.__func__.__code__
    return sorted({line for _, line in dis.findlinestarts(code)})


def extract_covered_lines(trace_text: str) -> list[int]:
    covered: set[int] = set()
    for raw_line in trace_text.splitlines():
        match = EVENT_RE.match(raw_line)
        if not match:
            continue
        if match.group("path") != str(TARGET_PATH):
            continue
        if match.group("func") != TARGET_FUNC:
            continue
        if match.group("event") != "line":
            continue
        covered.add(int(match.group("lineno")))
    if not covered:
        raise ValueError("No covered line events found for LiteralStringVar.create.")
    return sorted(covered)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log",
    )
    parser.add_argument(
        "--out",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json",
    )
    args = parser.parse_args()

    covered_lines = extract_covered_lines(Path(args.trace_log).read_text(encoding="utf-8"))
    target_lines = executable_lines()
    coverage_rate = round(len(set(covered_lines) & set(target_lines)) / len(target_lines), 4)
    print(
        f"coverage_rate={coverage_rate:.4f} "
        f"covered={len(set(covered_lines) & set(target_lines))} "
        f"executable={len(target_lines)}"
    )

    qa = {
        "question_kind": "coverage_prediction",
        "question": (
            "Run the full test suite in "
            "`tests/qa/vars_literal_string_create_line_coverage_suite_test.py` "
            "(all 10 test classes). Focus only on `reflex/vars/sequence.py`, class method "
            "`reflex.vars.sequence.LiteralStringVar.create` (lines 1167-1259). Count only "
            "line events whose traced function name is exactly "
            "`reflex.vars.sequence.LiteralStringVar.create`; do not include nested helper "
            "or called-function line events. The tests exercise this target indirectly by "
            "building encoded strings with Reflex Vars and then constructing literal string "
            "Vars. Which exact line numbers in the target method are covered at least once "
            "by this suite? Return a JSON object with exactly one key `covered_lines`, "
            "where the value is a sorted list of unique integers in ascending order: "
            "`{\\\"covered_lines\\\": [<int>, ...]}`."
        ),
        "template_answer": {
            "covered_lines": [],
        },
        "oracle_answer": {
            "covered_lines": covered_lines,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
