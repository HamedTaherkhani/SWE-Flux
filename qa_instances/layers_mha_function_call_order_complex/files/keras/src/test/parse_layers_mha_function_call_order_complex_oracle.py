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
    "layers/attention/multi_head_attention.py",
    "layers/core/einsum_dense.py",
    "layers/activations/softmax.py",
    "layers/regularization/dropout.py",
)


def extract_function_call_order(trace_text: str):
    order = []
    for file_path, line_no, func in CALL_RE.findall(trace_text):
        rel_file = file_path.replace("/testbed/", "")
        if rel_file.endswith(ALLOWED_SUFFIXES):
            order.append(
                {
                    "file": rel_file,
                    "line": int(line_no),
                    "func": func,
                }
            )
    if not order:
        raise ValueError("No function-call-order entries found for MHA complex QA.")
    return order


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/layers_mha_function_call_order_complex/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/layers_mha_function_call_order_complex/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    call_order = extract_function_call_order(trace_text)

    qa = {
        "question_kind": "function_call_order",
        "question": (
            "Use `keras/src/test/layers/attention/mha_function_call_order_complex_test.py`, "
            "class `MultiHeadAttentionFunctionCallOrderComplexQATest`, method "
            "`test_mha_function_call_order_with_masks_causal_and_dropout`. Setup: "
            "construct `MultiHeadAttention(num_heads=2, key_dim=2, value_dim=2, "
            "dropout=0.25, use_bias=True, seed=17)`, set query Keras mask to "
            "`[[True, True, False]]`, and call layer with explicit `query`, `value`, "
            "`key`, `value_mask=[[True, False, True, True]]`, "
            "`key_mask=[[True, True, False, True]]`, "
            "`attention_mask=[[[True, True, False, True], [True, False, False, True], "
            "[True, True, True, False]]]`, `return_attention_scores=True`, "
            "`training=True`, and `use_causal_mask=True`. "
            "What is the exact execution order of function calls for this test across "
            "`keras/src/layers/attention/multi_head_attention.py`, "
            "`keras/src/layers/core/einsum_dense.py`, "
            "`keras/src/layers/activations/softmax.py`, and "
            "`keras/src/layers/regularization/dropout.py`? "
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
