#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def extract_grads_shape(trace_text: str) -> list[int]:
    pattern = re.compile(
        r"_backend_apply_gradients .*'grads': '\[<tf\.Tensor: shape=\(([^)]*)\),",
        re.DOTALL,
    )
    matches = pattern.findall(trace_text)
    if not matches:
        raise ValueError("Could not find `grads` tensor shape in trace log.")
    shape_text = matches[-1]
    dims = [d.strip() for d in shape_text.split(",") if d.strip()]
    return [int(d) for d in dims]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_tensor_shape_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_tensor_shape_state/oracle.json",
    )
    args = parser.parse_args()

    trace_path = Path(args.trace_log)
    trace_text = trace_path.read_text(encoding="utf-8")
    grads_shape = extract_grads_shape(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `keras/src/test/optimizers/optimizers_tensor_shape_state_test.py`, "
            "class `OptimizersTensorShapeStateQATest`, method "
            "`test_grads_tensor_shape_after_clip_call`. Setup: "
            "`variable` is zeros with shape `(2, 3)` and dtype float32, "
            "`optimizer=SGD(learning_rate=0.5, clipvalue=0.2)`, and input "
            "`grads[0]` is the tensor "
            "`[[1.2, -0.5, 0.1], [0.7, -1.1, 2.0]]` (float32). "
            "During `optimizer.apply(grads, [variable])`, in "
            "`keras/src/optimizers/base_optimizer.py` method "
            "`_backend_apply_gradients`, right after the call "
            "`grads = self._clip_gradients(grads)` in the non-accumulation branch, "
            "what is the exact shape of tensor `grads[0]`?"
        ),
        "oracle_answer": grads_shape,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
