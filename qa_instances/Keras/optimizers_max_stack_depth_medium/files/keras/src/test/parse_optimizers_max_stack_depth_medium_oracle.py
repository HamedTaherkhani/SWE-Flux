#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# The benchmark stack depth is scoped to the filtered optimizer trace,
# not to the full Python interpreter stack.

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (/testbed/keras/src/[^:]+):(\d+) ([^ ]+) event=(call|return|exception) ",
    re.MULTILINE,
)


def compute_max_stack_depth(trace_text: str) -> int:
    depth = 0
    max_depth = 0
    for _file_path, _line_no, _func, event in EVENT_RE.findall(trace_text):
        if event == "call":
            depth += 1
            if depth > max_depth:
                max_depth = depth
        elif event in ("return", "exception"):
            depth = max(0, depth - 1)
    return max_depth


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_max_stack_depth_medium/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_max_stack_depth_medium/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    max_depth = compute_max_stack_depth(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `keras/src/test/optimizers/optimizers_max_stack_depth_medium_test.py`, "
            "class `OptimizersMaxStackDepthMediumQATest`, method "
            "`test_max_stack_depth_during_sgd_apply_with_clipnorm`. Setup: "
            "construct `SGD(learning_rate=0.08, momentum=0.6, nesterov=True, clipnorm=0.9)`, "
            "create 4 trainable variables and 4 gradient vectors as defined in the test, "
            "then call `optimizer.apply(grads, variables)`. "
            "Report the maximum nested call depth within the benchmark's traced optimizer scope. "
            "The scope is limited to trace records from `keras/src/optimizers/` whose function "
            "identifier matches the `keras.src.optimizers` trace filter. "
            "Do not report the full Python interpreter stack depth."
        ),
        "oracle_answer": {
            "max_stack_depth": max_depth,
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
