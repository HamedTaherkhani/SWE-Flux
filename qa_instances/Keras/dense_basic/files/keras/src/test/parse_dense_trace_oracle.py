#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

OUTPUTS_PATTERN = re.compile(
    r"test_dense_forward_pass .*locals=\{.*'outputs_np': 'array\((\[\[.*?\]\])(?:, dtype=.*?)?\)'",
    re.DOTALL,
)


def extract_output_matrix(trace_text: str) -> list[list[float]]:
    match = OUTPUTS_PATTERN.search(trace_text)
    if not match:
        raise ValueError("Could not find outputs_np for test_dense_forward_pass in trace log.")
    matrix_text = match.group(1)
    numbers = [float(n) for n in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", matrix_text)]
    if len(numbers) != 2:
        raise ValueError(f"Expected 2 output values, got {len(numbers)}: {numbers}")
    return [[numbers[0], numbers[1]]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default="/testbed/logs/dense_basic_trace.log")
    parser.add_argument("--out", default="/testbed/logs/dense_basic_qa_oracle.json")
    args = parser.parse_args()

    trace_path = Path(args.trace_log)
    trace_text = trace_path.read_text(encoding="utf-8")
    output = extract_output_matrix(trace_text)
    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `keras/src/test/layers/core/dense_basic_test.py`, class "
            "`DenseBasicTest`, method `test_dense_forward_pass` "
            "(method body lines 21-27). Setup is: instantiate "
            "`layers.Dense(units=2, use_bias=False)` on line 22, build with "
            "`layer.build((None, 2))` on line 23, set kernel weights to "
            "`[[1.0, -2.0], [3.0, -4.0]]` on line 24, then call the layer with "
            "input `[[-1.0, 2.0]]` on line 25 and convert to `outputs_np` on line 26. "
            "What exact numeric value does `outputs_np` contain?"
        ),
        "oracle_answer": output,
        "oracle_source": str(trace_path),
    }
    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
