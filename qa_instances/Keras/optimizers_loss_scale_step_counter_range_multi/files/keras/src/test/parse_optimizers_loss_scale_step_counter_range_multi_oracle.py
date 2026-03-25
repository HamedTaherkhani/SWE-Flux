#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STEP_LIST_RE = re.compile(r"step_counter_values': '\[([^\]]*)\]'")
INT_RE = re.compile(r"-?\d+")


def extract_values(trace_text: str) -> list[int]:
    values = []
    for arr in STEP_LIST_RE.findall(trace_text):
        values.extend(int(x) for x in INT_RE.findall(arr))
    if not values:
        raise ValueError("No step_counter_values were found in trace log.")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_loss_scale_step_counter_range_multi/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_loss_scale_step_counter_range_multi/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    values = extract_values(trace_text)

    qa = {
        "question_kind": "value_range_analysis",
        "question": (
            "Use `keras/src/test/optimizers/loss_scale_step_counter_range_multi_test.py`, "
            "class `LossScaleStepCounterRangeMultiQATest`, and all 12 test methods. "
            "These tests run multiple finite and non-finite gradient scenarios through "
            "`keras/src/optimizers/loss_scale_optimizer.py` (`LossScaleOptimizer.apply`, "
            "`_common_apply`, `_stateful_handle_finite_grads`, and "
            "`_stateful_handle_non_finite_grads`). In helper method "
            "`LossScaleStepCounterRangeMultiQATest._run_scenario`, each optimization step "
            "captures the runtime value of `optimizer.step_counter` after `optimizer.apply`. "
            "Across all 12 test methods, what is the observed range `[min, max]` of these "
            "`step_counter` values?"
        ),
        "oracle_answer": {
            "target_variable": "LossScaleOptimizer.step_counter (captured post-apply in _run_scenario)",
            "observed_min": min(values),
            "observed_max": max(values),
            "num_observations": len(values),
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
