#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


def extract_matching_keys(trace_text: str) -> list[str]:
    pattern = re.compile(
        r"'matching_keys':\s*(?:\"(\[.*?\])\"|'(\[.*?\])')",
        re.DOTALL,
    )
    matches = pattern.findall(trace_text)
    if not matches:
        raise ValueError("Could not find `matching_keys` in trace log.")
    raw = matches[-1][0] or matches[-1][1]
    return ast.literal_eval(raw.replace("\\n", "\n"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/distribution_layoutmap_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/distribution_layoutmap_state/oracle.json",
    )
    args = parser.parse_args()

    trace_path = Path(args.trace_log)
    trace_text = trace_path.read_text(encoding="utf-8")
    matching_keys = extract_matching_keys(trace_text)

    qa = {
        "question_kind": "variable_state_after_loop_before_exception_branch",
        "question": (
            "Use `keras/src/test/distribution/distribution_layoutmap_state_test.py`, "
            "class `DistributionLayoutMapStateQATest`, method "
            "`test_layoutmap_matching_keys_state_on_ambiguous_regex`. "
            "Setup: create `DeviceMesh(shape=(2,), axis_names=('batch',), "
            "devices=['cpu:0', 'cpu:1'])`; create `LayoutMap(device_mesh)`; "
            "insert two regex keys in this order: "
            "`'dense.*kernel' -> (None, 'batch')` and "
            "`'.*dense_1.*' -> ('batch', None)`; then query "
            "`layout_map['encoder/dense_1/kernel']` expecting ambiguity. "
            "In `keras/src/distribution/distribution_lib.py`, function "
            "`LayoutMap.__getitem__` (loop at lines 759-761 and branch check at "
            "line 762), what is the final value of local variable "
            "`matching_keys` immediately before the `if len(matching_keys) > 1` "
            "branch raises `ValueError`?"
        ),
        "oracle_answer": matching_keys,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
