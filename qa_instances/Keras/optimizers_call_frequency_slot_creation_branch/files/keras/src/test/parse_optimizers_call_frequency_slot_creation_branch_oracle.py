#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (/testbed/keras/src/[^:]+):(\d+) ([^ ]+) ",
    re.MULTILINE,
)

TARGET_FUNCTION = "keras.src.optimizers.base_optimizer.add_variable_from_reference"


def extract_calls(trace_text: str):
    calls = []
    for file_path, line_no, func in CALL_RE.findall(trace_text):
        calls.append(
            {
                "file": file_path.replace("/testbed/", ""),
                "line": int(line_no),
                "func": func,
            }
        )
    if not calls:
        raise ValueError("No call events found in trace log.")
    return calls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_call_frequency_slot_creation_branch/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_call_frequency_slot_creation_branch/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    calls = extract_calls(trace_text)
    call_count = sum(1 for c in calls if c["func"] == TARGET_FUNCTION)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `keras/src/test/optimizers/optimizers_call_frequency_slot_creation_branch_test.py`, "
            "class `OptimizersCallFrequencySlotCreationBranchQATest`, method "
            "`test_add_variable_from_reference_frequency_in_build_branch`. Setup: "
            "construct `SGD(learning_rate=0.1, momentum=0.5, nesterov=True, "
            "clipnorm=0.75)`, create 7 trainable variables `v0..v6` each with "
            "shape `(2,)`, and call `optimizer.apply(grads, variables)` with the "
            "7 gradient vectors defined in the test. In `keras/src/optimizers/base_optimizer.py`, "
            "during `optimizer.apply(...)`, the conditional branch where the optimizer "
            "is not yet built triggers slot-variable creation. Under this test, how many "
            "times is `keras.src.optimizers.base_optimizer.add_variable_from_reference` "
            "called?"
        ),
        "oracle_answer": {
            "target_function": TARGET_FUNCTION,
            "call_count": call_count,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
