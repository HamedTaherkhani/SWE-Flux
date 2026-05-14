#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/lib/matplotlib/bezier.py"
TARGET_FUNC = "matplotlib.bezier.find_bezier_t_intersecting_with_closedpath"
TARGET_LINE = 173

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _parse_changed_locals(raw_line: str) -> dict[str, object]:
    marker = " locals="
    index = raw_line.find(marker)
    if index < 0:
        return {}
    raw_locals = raw_line[index + len(marker):].strip()
    try:
        parsed = ast.literal_eval(raw_locals)
    except (SyntaxError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}

    decoded: dict[str, object] = {}
    for key, value in parsed.items():
        if isinstance(value, str):
            try:
                decoded[key] = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                decoded[key] = value
        else:
            decoded[key] = value
    return decoded


def extract_invariant(trace_text: str) -> dict[str, bool]:
    # Keep a per-invocation locals snapshot for the target function
    frame_stack: list[dict[str, object]] = []
    seen_any = False
    invariant_holds_for_all = True

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if m.group("path") != TARGET_PATH or m.group("func") != TARGET_FUNC:
            continue

        event = m.group("event")
        lineno = int(m.group("lineno"))

        if event == "call":
            frame_stack.append({})
            continue

        if event in {"return", "exception"}:
            if frame_stack:
                frame_stack.pop()
            continue

        if event != "line" or not frame_stack:
            continue

        changed = _parse_changed_locals(raw_line)
        if changed:
            frame_stack[-1].update(changed)

        if lineno != TARGET_LINE:
            continue

        current = frame_stack[-1]
        # At line 173: t1 = middle_t (in the first branch of the if-else)
        # Check the invariant: before this assignment, t0 < t1 should hold
        if "t0" not in current or "t1" not in current:
            continue
        
        t0 = current["t0"]
        t1 = current["t1"]
        if not isinstance(t0, (int, float)) or not isinstance(t1, (int, float)):
            continue
        
        seen_any = True
        # The invariant: t0 < t1 (strictly less than, not <=)
        invariant = t0 < t1
        if not invariant:
            invariant_holds_for_all = False

    return {"invariant_exists": seen_any and invariant_holds_for_all}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "bezier_bisection_t0_less_t1_invariant_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "bezier_bisection_t0_less_t1_invariant_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_invariant(trace_text)

    qa = {
        "question_kind": "M7_Invariants",
        "question": (
            "Use the full test suite in "
            "`tests/qa/bezier_bisection_t0_less_t1_invariant_suite_test.py` "
            "(all test cases in class "
            "`TestBezierBisectionT0LessT1InvariantSuiteQA`, 25 tests). "
            "Each test calls `find_bezier_t_intersecting_with_closedpath(bezier_point_at_t, "
            "inside_closedpath, t0=0., t1=1., tolerance)` with different Bézier curves. "
            "Focus on `lib/matplotlib/bezier.py`, function "
            "`matplotlib.bezier.find_bezier_t_intersecting_with_closedpath`. "
            "At line `173` (`t1 = middle_t`), consider local variables `t0` and `t1`. "
            "Across all evaluations of this line over the full suite (including multiple loop "
            "iterations within each test), is the property `t0 < t1` an invariant property? "
            "Return JSON as `{\\\"invariant_exists\\\": <bool>}` where `true` means the property "
            "holds for every evaluation and `false` means it does not hold."
        ),
        "template_answer": {
            "invariant_exists": "bool"
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
