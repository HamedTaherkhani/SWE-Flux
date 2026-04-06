#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (/testbed/keras/src/optimizers/[^:]+):(\d+) ([^ ]+) ",
    re.MULTILINE,
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
        if rel_file.endswith("base_optimizer.py") or rel_file.endswith("sgd.py"):
            path.append(
                {
                    "file": rel_file,
                    "line": int(line_no),
                    "func": normalize_func_identifier(func),
                }
            )
    if not path:
        raise ValueError("No execution path entries found for optimizer files.")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_execution_path_multi/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_execution_path_multi/oracle.json",
    )
    args = parser.parse_args()

    trace_path = Path(args.trace_log)
    trace_text = trace_path.read_text(encoding="utf-8")
    execution_path = extract_execution_path(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `keras/src/test/optimizers/optimizers_execution_path_multi_test.py`, "
            "class `OptimizersExecutionPathMultiQATest`, method "
            "`test_exact_execution_path_across_optimizer_files`. Setup: "
            "`variable=[1.0, -1.0]` (float32), "
            "`optimizer=SGD(learning_rate=0.2, momentum=0.9, nesterov=True, clipvalue=0.5)`, "
            "and input gradient tensor `grads[0]=[1.7, -0.3]` (float32). "
            "When calling `optimizer.apply(grads, [variable])`, what exact execution "
            "path is taken across optimizer project files? Return the ordered full path "
            "as entries of `{file, line, func}` for "
            "`keras/src/optimizers/base_optimizer.py` and "
            "`keras/src/optimizers/sgd.py`."
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
