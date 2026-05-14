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

ALLOWED_SUFFIXES = (
    "layers/convolutional/conv2d.py",
    "layers/convolutional/base_conv.py",
    "activations/activations.py",
    "backend/tensorflow/nn.py",
)


def normalize_func_identifier(func: str) -> str:
    if "|||" in func:
        full_path, short_name = func.split("|||", 1)
        if short_name:
            return f"{full_path}|||{short_name}"
        func = full_path
    short_name = func.rsplit(".", 1)[-1]
    return f"{func}|||{short_name}"


def extract_call_order(trace_text: str):
    order = []
    for file_path, line_no, func in CALL_RE.findall(trace_text):
        rel_file = file_path.replace("/testbed/", "")
        if rel_file.endswith(ALLOWED_SUFFIXES):
            order.append(
                {
                    "file": rel_file,
                    "line": int(line_no),
                    "func": normalize_func_identifier(func),
                }
            )
    if not order:
        raise ValueError("No function call order entries found for Conv2D hard QA.")
    return order


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/layers_conv2d_function_call_order_hard/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/layers_conv2d_function_call_order_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    call_order = extract_call_order(trace_text)

    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `keras/src/test/layers/convolutional/conv2d_function_call_order_hard_test.py`, "
            "class `Conv2DFunctionCallOrderHardQATest`, method "
            "`test_conv2d_function_call_order_grouped_channels_first_bias_activation`. "
            "Setup: construct `Conv2D(filters=4, kernel_size=(3, 3), strides=(1, 1), "
            "padding='same', data_format='channels_first', dilation_rate=(1, 1), "
            "groups=2, activation='relu', use_bias=True)` and call it on the test "
            "input tensor of shape `(1, 4, 6, 6)`. "
            "What is the exact execution order of function calls triggered by this "
            "test across `keras/src/layers/convolutional/conv2d.py`, "
            "`keras/src/layers/convolutional/base_conv.py`, "
            "`keras/src/activations/activations.py`, and "
            "`keras/src/backend/tensorflow/nn.py`? "
            "Return ordered entries as `{file, line, func}`."
        ),
        "oracle_answer": {
            "function_call_order": call_order,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
