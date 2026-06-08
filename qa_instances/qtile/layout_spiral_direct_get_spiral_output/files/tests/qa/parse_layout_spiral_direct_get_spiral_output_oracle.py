#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/layout/spiral\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.layout\.spiral\.(?:Spiral\.)?get_spiral) "
    r"event=return retval=(?P<retval>.*?) locals=\{.*\}$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find Spiral.get_spiral return events in trace log.")

    target = matches[-1]
    retval = target.group("retval").strip()

    parsed = ast.literal_eval(retval)
    if not isinstance(parsed, list):
        raise ValueError("Expected Spiral.get_spiral retval to be a list.")

    output_rectangles = []
    for rect in parsed:
        if not isinstance(rect, tuple) or len(rect) != 4:
            raise ValueError("Expected each rectangle to be a 4-tuple.")
        output_rectangles.append([int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])])

    return {"output_rectangles": output_rectangles}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/layout_spiral_direct_get_spiral_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/layout_spiral_direct_get_spiral_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/layout_spiral_direct_get_spiral_output_test.py`, class "
            "`TestLayoutSpiralDirectGetSpiralOutputQA`, method "
            "`test_layout_spiral_direct_get_spiral_output_case`. "
            "In that test, lines 5-12 build a `Spiral` layout instance with explicit "
            "`main_pane`, `clockwise`, `ratio`, `margin`, and `border_width` settings, "
            "line 15 injects 15 pseudo-clients into `spiral.clients.clients`, and line 17 "
            "directly calls `spiral.get_spiral(23, 47, 1621, 941)`. "
            "In `libqtile/layout/spiral.py`, `Spiral.get_spiral` (defined at line 301) "
            "iteratively splits rectangles and can stop early when `has_invalid_size` is hit. "
            "What is the exact returned list of rectangles `(x, y, w, h)` from this direct call?"
        ),
        "template_answer": {
            "output_rectangles": [["int", "int", "int", "int"]]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
