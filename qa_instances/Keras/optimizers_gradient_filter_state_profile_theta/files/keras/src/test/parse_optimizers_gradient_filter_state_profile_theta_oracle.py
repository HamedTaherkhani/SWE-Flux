#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


def extract_missing_grad_vars(trace_text: str) -> list[str]:
    pattern = re.compile(
        r"'missing_grad_vars':\s*(?:\"(\[.*?\])\"|'(\[.*?\])')",
        re.DOTALL,
    )
    matches = pattern.findall(trace_text)
    if not matches:
        raise ValueError("Could not find `missing_grad_vars` in trace log.")
    raw = matches[-1][0] or matches[-1][1]
    return ast.literal_eval(raw.replace("\\n", "\n"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_gradient_filter_state_profile_theta/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_gradient_filter_state_profile_theta/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    missing_grad_vars = extract_missing_grad_vars(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `keras/src/test/optimizers/optimizers_gradient_filter_state_profile_theta_test.py`, "
            "class `OptimizersGradientFilterStateProfileThetaQATest`, method "
            "`test_missing_grad_paths_before_empty_grad_exception`. In this method, "
            "an `SGD` optimizer calls `optimizer._filter_empty_gradients(grads, variables)` with "
            "`grads=[None, None, None, None]` and four probe variables whose `path` values are "
            "`'encoder/block_0/attn/query_kernel'`, `'encoder/block_0/attn/query_bias'`, "
            "`'encoder/block_1/mlp/output_kernel'`, and `'head/projection/kernel'`. "
            "In `keras/src/optimizers/base_optimizer.py`, method "
            "`BaseOptimizer._filter_empty_gradients`, the reverse loop at lines 761-770 "
            "updates local variable `missing_grad_vars` before the branch "
            "`if not filtered_grads:` at lines 771-772 raises `ValueError`. "
            "What is the final value of `missing_grad_vars` immediately before that exception branch?"
        ),
        "oracle_answer": missing_grad_vars,
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
