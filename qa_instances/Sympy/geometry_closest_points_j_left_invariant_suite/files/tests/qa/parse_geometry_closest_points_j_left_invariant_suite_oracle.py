#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/sympy/geometry/util.py"
TARGET_FUNC = "sympy.geometry.util.closest_points"
TARGET_LINE = 347

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/geometry/[^:]+):(?P<lineno>\d+) "
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
    # stack of per-frame local snapshots for closest_points calls
    frame_locals_stack: list[dict[str, object]] = []
    seen_any = False
    relation_holds_for_all = True

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue

        if m.group("path") != TARGET_PATH or m.group("func") != TARGET_FUNC:
            continue

        event = m.group("event")
        lineno = int(m.group("lineno"))

        if event == "call":
            frame_locals_stack.append({})
            continue

        if event in {"return", "exception"}:
            if frame_locals_stack:
                frame_locals_stack.pop()
            continue

        if event != "line" or not frame_locals_stack:
            continue

        changed = _parse_changed_locals(raw_line)
        if changed:
            frame_locals_stack[-1].update(changed)

        if lineno != TARGET_LINE:
            continue

        current = frame_locals_stack[-1]
        if "j" not in current or "left" not in current:
            continue
        if not isinstance(current["j"], int) or not isinstance(current["left"], int):
            continue

        seen_any = True
        relation = current["j"] >= current["left"]
        if not relation:
            relation_holds_for_all = False

    invariant_exists = seen_any and relation_holds_for_all
    return {"invariant_exists": invariant_exists}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "geometry_closest_points_j_left_invariant_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "geometry_closest_points_j_left_invariant_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_invariant(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in "
            "`tests/qa/geometry_closest_points_j_left_invariant_suite_test.py` "
            "(all generated test cases in class "
            "`TestGeometryClosestPointsJLeftInvariantSuiteQA`, 24 tests). "
            "Focus on `sympy/geometry/util.py`, function "
            "`sympy.geometry.util.closest_points`. "
            "At line `347` (`d = hypot(p[i].x - p[j].x, p[i].y - p[j].y)`), "
            "consider local variables `j` and `left` in the current invocation frame. "
            "Across all evaluations of this line over the full suite, is the relationship "
            "`j >= left` an invariant property? "
            "Return JSON as `{\\\"invariant_exists\\\": <bool>}` where `true` means the "
            "relationship holds for every evaluation and `false` means it does not hold."
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
