#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|return|exception) ",
    re.MULTILINE,
)


def extract_max_depth(trace_text: str) -> dict:
    depth = 0
    max_depth = 0

    for match in EVENT_RE.finditer(trace_text):
        event = match.group("event")
        if event == "call":
            depth += 1
            if depth > max_depth:
                max_depth = depth
        elif event in {"return", "exception"}:
            depth = max(0, depth - 1)

    return {"maximum_call_stack_depth": max_depth}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/solvers_lambert_max_call_depth/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/solvers_lambert_max_call_depth/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_max_depth(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `tests/qa/solvers_lambert_max_call_depth_test.py`, class "
            "`TestSolversLambertMaxCallDepthQA`, method `test_solvers_lambert_max_call_depth_case`. "
            "At line 9, `solutions = solve(x + exp(x), x, dict=True)` is executed. "
            "Compute call stack depth over the whole project scope `sympy/` "
            "(i.e., all traced events from files under `/testbed/sympy/` only, excluding Python/internal library frames). "
            "What is the maximum call stack depth reached during the entire execution of this test run?"
        ),
        "template_answer": {
            "maximum_call_stack_depth": "int"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
