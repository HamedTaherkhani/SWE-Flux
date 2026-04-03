#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|return|exception)\b",
    re.MULTILINE,
)


def extract_max_depth(trace_text: str) -> dict[str, int]:
    depth = 0
    max_depth = 0
    seen_any = False

    for m in EVENT_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if "/xarray/core/" not in path:
            continue

        seen_any = True
        event = m.group("event")
        if event == "call":
            depth += 1
            if depth > max_depth:
                max_depth = depth
        else:
            depth = max(depth - 1, 0)

    if not seen_any:
        raise ValueError("Could not find xarray/core call-stack events in trace log.")

    return {"max_call_stack_depth": max_depth}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/combine_by_coords_max_call_depth_hard/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/combine_by_coords_max_call_depth_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_max_depth(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `xarray/tests/qa/combine_by_coords_max_call_depth_hard_test.py`, class "
            "`TestCombineByCoordsMaxCallDepthHardQA`, method "
            "`test_combine_by_coords_max_call_depth_hard_case`. "
            "At line 33, `xr.combine_by_coords(...)` is executed on four `Dataset` objects. "
            "Trace the full execution of this test call and consider call-stack nesting over "
            "all traced events from files under `xarray/core/` (using `event=call`, `event=return`, "
            "and `event=exception`). What is the maximum call stack depth reached during this run?"
        ),
        "template_answer": {"max_call_stack_depth": "int"},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
