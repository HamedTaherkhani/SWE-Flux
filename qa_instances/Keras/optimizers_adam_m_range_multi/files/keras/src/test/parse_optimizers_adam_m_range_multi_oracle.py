#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

M_RE = re.compile(r"'m': '<Variable[^']*value=\[([^\]]+)\]>'")
FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def extract_m_values(trace_text: str) -> list[float]:
    values = []
    for arr in M_RE.findall(trace_text):
        nums = [float(x) for x in FLOAT_RE.findall(arr)]
        values.extend(nums)
    if not values:
        raise ValueError("No Adam momentum slot (`m`) values were found in trace log.")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/optimizers_adam_m_range_multi/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/optimizers_adam_m_range_multi/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    values = extract_m_values(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use `keras/src/test/optimizers/adam_m_range_multi_test.py`, class "
            "`AdamMRangeMultiQATest`, and all 12 test methods in this class. "
            "Each test runs one Adam scenario with different hyperparameters "
            "(including both `amsgrad=True/False`) and multi-step gradient sequences "
            "over two variables. In `keras/src/optimizers/adam.py`, inside "
            "`Adam.update_step`, what is the observed value range `[min, max]` of the "
            "local momentum slot variable `m` across the full execution of this entire "
            "test class?"
        ),
        "oracle_answer": {
            "target_variable": "Adam.update_step local `m` slot value",
            "observed_min": min(values),
            "observed_max": max(values),
            "num_observations": len(values),
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
