#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/libqtile/backend/wayland/(?:inputs|window)\.py):(?P<lineno>\d+) "
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
        default=(
            "/testbed/logs/qa_instances/"
            "backend_wayland_inputs_direct_repeat_key_max_call_depth/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "backend_wayland_inputs_direct_repeat_key_max_call_depth/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_max_depth(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `tests/qa/backend_wayland_inputs_direct_repeat_key_max_call_depth_test.py`, class "
            "`TestBackendWaylandInputsDirectRepeatKeyMaxCallDepthQA`, method "
            "`test_backend_wayland_inputs_direct_repeat_key_max_call_depth_case`. "
            "This is a direct backend Wayland test centered on `Keyboard._on_repeat_key` in "
            "`libqtile/backend/wayland/inputs.py`; during key processing it also executes chained "
            "floating-window helpers from `libqtile/backend/wayland/window.py`, including "
            "`Window.move_floating`, `Window._tweak_float`, `Window._reconfigure_floating`, and "
            "`Window.paint_borders`. "
            "Compute call stack depth over the combined scope of these two files only: "
            "`libqtile/backend/wayland/inputs.py` and `libqtile/backend/wayland/window.py` "
            "(include only traced `call`/`return`/`exception` events from those files; exclude all other files). "
            "What is the maximum call stack depth reached during the entire test run?"
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
