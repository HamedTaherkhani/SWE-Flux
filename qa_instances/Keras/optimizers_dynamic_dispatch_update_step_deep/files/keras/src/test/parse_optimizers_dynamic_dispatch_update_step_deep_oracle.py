#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (/testbed/keras/src/[^:]+):(\d+) ([^ ]+) event=(call|return|exception) ",
    re.MULTILINE,
)

DISPATCH_CALLSITE_FUNC = (
    "keras.src.optimizers.base_optimizer._backend_apply_gradients"
)
DISPATCH_CALLSITE_FILE = "keras/src/optimizers/base_optimizer.py"
DISPATCH_CALLSITE_LINE = 454
# The benchmark anchors this question at the outer trace-visible dispatch site
# in `_backend_apply_gradients`, not at the inner helper `_backend_update_step`.
# The graded `dispatched_function` is the first non-`base_optimizer.py`
# `.update_step` call that appears after that anchor in the trace log, reported
# using the trace log's module-level function identifier.


def infer_class_name(file_path: str) -> str:
    name = Path(file_path).stem
    return "".join(part.capitalize() for part in name.split("_"))


def normalize_func_identifier(func: str) -> str:
    if "|||" in func:
        full_path, short_name = func.split("|||", 1)
        if short_name:
            return f"{full_path}|||{short_name}"
        func = full_path
    short_name = func.rsplit(".", 1)[-1]
    return f"{func}|||{short_name}"


def extract_dispatched_update_step(trace_text: str):
    events = [
        {
            "file": file_path.replace("/testbed/", ""),
            "line": int(line_no),
            "func": func,
            "event": event,
        }
        for file_path, line_no, func, event in EVENT_RE.findall(trace_text)
    ]
    if not events:
        raise ValueError("No events found in trace log.")

    for i, ev in enumerate(events):
        if (
            ev["event"] == "call"
            and ev["file"] == DISPATCH_CALLSITE_FILE
            and ev["func"] == DISPATCH_CALLSITE_FUNC
        ):
            for nxt in events[i + 1 :]:
                if nxt["event"] != "call":
                    continue
                if nxt["func"].endswith(".update_step") and not nxt["file"].endswith(
                    "base_optimizer.py"
                ):
                    return {
                        "dispatched_function": normalize_func_identifier(nxt["func"]),
                        "dispatched_file": nxt["file"],
                        "concrete_class": infer_class_name(nxt["file"]),
                    }
    raise ValueError("Could not find dispatched concrete update_step call.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_dynamic_dispatch_update_step_deep/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_dynamic_dispatch_update_step_deep/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    dispatched = extract_dispatched_update_step(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `keras/src/test/optimizers/optimizers_dynamic_dispatch_update_step_deep_test.py`, "
            "class `OptimizersDynamicDispatchUpdateStepDeepQATest`, method "
            "`test_concrete_update_step_dispatched_from_base_backend_update_step`. Setup: "
            "construct `LossScaleOptimizer(Adam(learning_rate=0.01, beta_1=0.8, "
            "beta_2=0.95, amsgrad=True, clipnorm=0.7), initial_scale=128.0, "
            "dynamic_growth_steps=2)`, create 3 trainable variables and call "
            "`optimizer.apply(...)` first with finite grads and then with non-finite "
            "grads containing NaN, as defined in the test. In "
            "`keras/src/optimizers/base_optimizer.py` at line 454 inside "
            "`_backend_apply_gradients`, the code enters the update-dispatch path "
            "that invokes `update_step(...)` on the concrete optimizer. "
            "Return a JSON object with exactly these fields: `concrete_class`, "
            "`dispatch_callsite`, `dispatched_file`, and `dispatched_function`. "
            "For `dispatch_callsite`, report the outer trace-visible dispatch anchor as "
            "`{file: 'keras/src/optimizers/base_optimizer.py', line: 454, func: "
            "'keras.src.optimizers.base_optimizer._backend_apply_gradients'}`. "
            "For `dispatched_file` and `dispatched_function`, report the first "
            "non-`base_optimizer.py` `.update_step` call reached after that anchor, "
            "using the trace log's fully qualified module-level function identifier "
            "(not an inner helper such as `_backend_update_step` and not a bound-method "
            "label such as `Adam.update_step`). Which concrete class's `update_step` "
            "implementation was actually executed for that dispatched call?"
        ),
        "oracle_answer": {
            "dispatch_callsite": {
                "file": DISPATCH_CALLSITE_FILE,
                "line": DISPATCH_CALLSITE_LINE,
                "func": normalize_func_identifier(DISPATCH_CALLSITE_FUNC),
            },
            **dispatched,
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
