#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def extract_project_exception(trace_text: str) -> dict:
    pattern = re.compile(
        r"_filter_empty_gradients .* exc=([A-Za-z_][A-Za-z0-9_]*): (.*?) locals=",
        re.DOTALL,
    )
    matches = pattern.findall(trace_text)
    if not matches:
        raise ValueError(
            "Could not find project exception event from `_filter_empty_gradients`."
        )
    exc_type, exc_message = matches[-1]
    msg = exc_message.strip()
    wrapper_prefix = f"{exc_type}('"
    if msg.startswith(wrapper_prefix) and msg.endswith("')"):
        msg = msg[len(wrapper_prefix) : -2]
    return {
        "exception_type": exc_type.strip(),
        "exception_message": msg,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_project_exception_deep/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_project_exception_deep/oracle.json",
    )
    args = parser.parse_args()

    trace_path = Path(args.trace_log)
    trace_text = trace_path.read_text(encoding="utf-8")
    exception_data = extract_project_exception(trace_text)

    qa = {
        "question_kind": "S6_Exceptions",
        "question": (
            "Use `keras/src/test/optimizers/optimizers_project_exception_deep_test.py`, "
            "class `OptimizersProjectExceptionDeepQATest`, method "
            "`test_exception_from_filter_empty_gradients_path`. Setup: "
            "`variable=[1.0, -2.0, 3.0]` (float32), "
            "`optimizer=SGD(learning_rate=0.1, gradient_accumulation_steps=2)`, "
            "`grads=[None]`, and `trainable_variables=[variable]`. The method calls "
            "`optimizer.apply(grads, trainable_variables)`. Inside project code in "
            "`keras/src/optimizers/base_optimizer.py`, this reaches "
            "`BaseOptimizer._filter_empty_gradients`, where empty gradients are "
            "filtered and an exception is raised. What exact exception signature "
            "(type and message) is raised by the project code at that location?"
        ),
        "oracle_answer": exception_data,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
