#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/.*?):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|return|exception)",
    re.MULTILINE,
)


def compute_max_call_depth(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find any traced events for call depth calculation.")

    current_depth = 0
    max_depth = 0

    for match in matches:
        event = match.group("event")
        if event == "call":
            current_depth += 1
            if current_depth > max_depth:
                max_depth = current_depth
        elif event in ("return", "exception"):
            current_depth = max(0, current_depth - 1)

    return {"maximum_call_stack_depth": max_depth}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/mathtext_nested_frac_ship_max_call_depth/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/mathtext_nested_frac_ship_max_call_depth/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = compute_max_call_depth(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `tests/qa/mathtext_nested_frac_ship_max_call_depth_test.py`, class "
            "`TestMathtextNestedFracShipMaxCallDepthQA`, method "
            "`test_mathtext_nested_frac_ship_max_call_depth_case`. "
            "The test builds a valid mathtext string with 24 levels of nested `\\frac{...}{y}` "
            "around a leaf `x`, then calls `MathTextParser('path').parse(expr, dpi=96)`. "
            "That execution path exercises `matplotlib.mathtext.MathTextParser._parse_cached`, "
            "`matplotlib._mathtext.Parser.parse` (pyparsing-driven), box construction, and "
            "`matplotlib._mathtext.ship` with mutually recursive `hlist_out` / `vlist_out` closures "
            "over a deep `Hlist`/`Vlist` tree. "
            "Compute call stack depth over the whole project scope `/testbed/lib/matplotlib/` "
            "(include only traced call/return/exception events from files under this directory; "
            "exclude frames from the standard library and third-party packages such as pyparsing "
            "and numpy). "
            "What is the maximum call stack depth reached during the entire execution of this test run?"
        ),
        "template_answer": {
            "maximum_call_stack_depth": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
