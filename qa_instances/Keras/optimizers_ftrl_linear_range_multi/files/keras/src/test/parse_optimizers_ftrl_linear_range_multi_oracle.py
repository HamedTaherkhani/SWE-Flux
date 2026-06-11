#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINEAR_RE = re.compile(r"'linear': '<Variable[^']*value=\[([^\]]+)\]>'")
FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def extract_linear_values(trace_text: str):
    values = []
    for arr in LINEAR_RE.findall(trace_text):
        nums = [float(x) for x in FLOAT_RE.findall(arr)]
        values.extend(nums)
    if not values:
        raise ValueError("No linear variable values were found in trace log.")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_ftrl_linear_range_multi/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_ftrl_linear_range_multi/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    values = extract_linear_values(trace_text)
    observed_min = min(values)
    observed_max = max(values)

    qa = {
        "question_kind": "M3_ProgramState",
        "question": (
            "Use `keras/src/test/optimizers/ftrl_linear_range_multi_test.py`, class "
            "`FtrlLinearRangeMultiQATest`, and all 12 test methods in this class. "
            "Each test runs one FTRL scenario with different hyperparameters and "
            "multi-step gradient sequences. In `keras/src/optimizers/ftrl.py`, inside "
            "`Ftrl.update_step`, what is the observed value range `[min, max]` of the "
            "internal optimizer slot variable `linear` across the full execution of this "
            "entire test class?"
        ),
        "oracle_answer": {
            "target_variable": "Ftrl.update_step local `linear` slot value",
            "observed_min": observed_min,
            "observed_max": observed_max
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
