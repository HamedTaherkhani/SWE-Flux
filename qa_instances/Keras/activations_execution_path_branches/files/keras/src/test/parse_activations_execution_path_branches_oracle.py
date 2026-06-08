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

ALLOWED_SUFFIXES = (
    "activations/activations.py",
    "backend/tensorflow/nn.py",
    "backend/tensorflow/numpy.py",
)


def normalize_func_identifier(func: str) -> str:
    if "|||" in func:
        full_path, short_name = func.split("|||", 1)
        if short_name:
            return f"{full_path}|||{short_name}"
        func = full_path
    short_name = func.rsplit(".", 1)[-1]
    return f"{func}|||{short_name}"


def extract_execution_path(trace_text: str):
    path = []
    for file_path, line_no, func in LINE_RE.findall(trace_text):
        rel_file = file_path.replace("/testbed/", "")
        if rel_file.endswith(ALLOWED_SUFFIXES):
            path.append(
                {
                    "file": rel_file,
                    "line": int(line_no),
                    "func": normalize_func_identifier(func),
                }
            )
    if not path:
        raise ValueError("No activation execution path entries found.")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/activations_execution_path_branches/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/activations_execution_path_branches/oracle.json",
    )
    args = parser.parse_args()

    trace_path = Path(args.trace_log)
    trace_text = trace_path.read_text(encoding="utf-8")
    execution_path = extract_execution_path(trace_text)

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `keras/src/test/activations/activations_execution_path_branches_test.py`, "
            "class `ActivationsExecutionPathBranchesQATest`, method "
            "`test_relu_full_execution_path_branch_code`. Setup: "
            "`x=[-1.0, 0.1, 0.4, 2.0]` (float32) and call "
            "`keras.src.activations.activations.ReLU.static_call(x, negative_slope=0.3, "
            "max_value=1.5, threshold=0.2)`. "
            "Considering only the branch-based under-test functions (no loop-based "
            "functions), what exact full execution path is taken across project files "
            "`keras/src/activations/activations.py`, "
            "`keras/src/backend/tensorflow/nn.py`, and "
            "`keras/src/backend/tensorflow/numpy.py`? "
            "Return the ordered path entries as `{file, line, func}`."
        ),
        "oracle_answer": {
            "executed_path": execution_path,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
