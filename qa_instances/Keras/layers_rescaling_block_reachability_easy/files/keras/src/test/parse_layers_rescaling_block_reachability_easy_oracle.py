#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (/testbed/keras/src/[^:]+):(\d+) ([^ ]+) ",
    re.MULTILINE,
)

TARGET_FILE = "keras/src/layers/preprocessing/rescaling.py"
TARGET_BLOCK_LINES = [50, 51]


def normalize_func_identifier(func: str) -> str:
    if "|||" in func:
        full_path, short_name = func.split("|||", 1)
        if short_name:
            return f"{full_path}|||{short_name}"
        func = full_path
    short_name = func.rsplit(".", 1)[-1]
    return f"{func}|||{short_name}"


def extract_events(trace_text: str):
    events = []
    for file_path, line_no, func in LINE_RE.findall(trace_text):
        rel_file = file_path.replace("/testbed/", "")
        events.append(
            {
                "file": rel_file,
                "line": int(line_no),
                "func": normalize_func_identifier(func),
            }
        )
    if not events:
        raise ValueError("No trace events found.")
    return events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/layers_rescaling_block_reachability_easy/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/layers_rescaling_block_reachability_easy/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    events = extract_events(trace_text)

    executed_lines = {
        e["line"]
        for e in events
        if e["file"] == TARGET_FILE
    }
    block_executed = all(line in executed_lines for line in TARGET_BLOCK_LINES)

    qa = {
        "question_kind": "S1_IntraProceduralCFG",
        "question": (
            "Use `keras/src/test/layers/preprocessing/rescaling_block_reachability_easy_test.py`, "
            "class `RescalingBlockReachabilityEasyQATest`, method "
            "`test_channels_first_scale_reshape_block_reachability`. Setup: set "
            "global image data format to `channels_first`, construct "
            "`Rescaling(scale=[0.5, 1.0, 1.5], offset=0.25)`, and call it on "
            "input tensor of shape `(1, 3, 2, 2)` as defined in the test. "
            "In `keras/src/layers/preprocessing/rescaling.py`, inside "
            "`Rescaling.call`, is the branch block at lines 50-51 (the scale "
            "reshape block under the channels-first condition) ever executed?"
        ),
        "oracle_answer": {
            "is_executed": block_executed
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
