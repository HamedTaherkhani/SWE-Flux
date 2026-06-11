#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/layout/ratiotile\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.layout\.ratiotile\.(?:GridInfo\.)?get_sizes_advanced) "
    r"event=return retval=(?P<retval>.*?) locals=\{.*\}$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find GridInfo.get_sizes_advanced return events in trace log.")

    target = matches[-1]
    retval = target.group("retval").strip()

    parsed = ast.literal_eval(retval)
    if not isinstance(parsed, list):
        raise ValueError("Expected GridInfo.get_sizes_advanced retval to be a list.")

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
        default=(
            "/testbed/logs/qa_instances/"
            "ratiotile_gridinfo_direct_get_sizes_advanced_output/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "ratiotile_gridinfo_direct_get_sizes_advanced_output/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/ratiotile_gridinfo_direct_get_sizes_advanced_output_test.py`, class "
            "`TestRatioTileGridInfoDirectGetSizesAdvancedOutputQA`, method "
            "`test_ratiotile_gridinfo_direct_get_sizes_advanced_output_case`. "
            "In that test, line 6 creates `GridInfo(ratio=0.63, num_windows=13, width=711, "
            "height=1009)` and line 8 directly calls "
            "`grid.get_sizes_advanced(711, 1009, 17, 29)`. "
            "In `libqtile/layout/ratiotile.py`, `GridInfo.get_sizes_advanced` (defined at line "
            "107) repeatedly recalculates orientation and remaining area while appending window "
            "rectangles. What is the exact returned list of rectangles `(x, y, w, h)` from this "
            "direct call?"
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
