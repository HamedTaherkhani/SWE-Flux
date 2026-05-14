#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def extract_clipped_grads(trace_text: str) -> list[float]:
    pattern = re.compile(
        r"_backend_apply_gradients .*'grads': '\[<tf\.Tensor:.*?numpy=array\(\[([^\]]+)\], dtype=float32\)>\]'",
        re.DOTALL,
    )
    matches = pattern.findall(trace_text)
    if not matches:
        raise ValueError("Could not find clipped `grads` state in trace log.")
    values_text = matches[-1]
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", values_text)
    if len(nums) != 3:
        raise ValueError(f"Expected 3 gradient values, got {len(nums)}: {nums}")
    return [float(nums[0]), float(nums[1]), float(nums[2])]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_clip_call_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_clip_call_state/oracle.json",
    )
    args = parser.parse_args()

    trace_path = Path(args.trace_log)
    trace_text = trace_path.read_text(encoding="utf-8")
    clipped_grads = extract_clipped_grads(trace_text)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `keras/src/test/optimizers/optimizers_clip_call_state_test.py`, "
            "class `OptimizersClipCallStateQATest`, method "
            "`test_grads_state_after_clip_call`. Setup: "
            "`variable=[0.0, 0.0, 0.0]` (float32), "
            "`optimizer=SGD(learning_rate=1.0, clipvalue=0.25)`, and "
            "input gradient tensor `[1.2, -0.5, 0.1]` (float32). "
            "The method calls `optimizer.apply(grads, [variable])`, which enters "
            "`keras/src/optimizers/base_optimizer.py` method "
            "`_backend_apply_gradients`; in the non-accumulation branch, it executes "
            "`grads = self._clip_gradients(grads)` before update_step. "
            "What is the exact numeric value of local variable `grads[0]` "
            "immediately after that `_clip_gradients(grads)` call?"
        ),
        "oracle_answer": clipped_grads,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
