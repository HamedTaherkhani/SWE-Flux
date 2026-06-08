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
    "layers/attention/grouped_query_attention.py",
    "layers/core/einsum_dense.py",
    "layers/activations/softmax.py",
    "layers/regularization/dropout.py",
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
        raise ValueError("No call-order entries found for GQA hard QA.")
    return order


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/layers_gqa_function_call_order_hard/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/layers_gqa_function_call_order_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    call_order = extract_call_order(trace_text)

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `keras/src/test/layers/attention/gqa_function_call_order_hard_test.py`, "
            "class `GroupedQueryAttentionFunctionCallOrderHardQATest`, method "
            "`test_gqa_function_call_order_with_repeats_masks_causal_dropout`. "
            "Setup: construct `GroupedQueryAttention(head_dim=2, num_query_heads=6, "
            "num_key_value_heads=2, dropout=0.3, use_bias=True, seed=31)` and call it "
            "with `query` shape `(1, 4, 6)`, `value` shape `(1, 5, 6)`, `key=None`, "
            "`query_mask=[[True, True, False, True]]`, "
            "`value_mask=[[True, False, True, True, True]]`, "
            "`key_mask=[[True, True, False, True, True]]`, "
            "`attention_mask` as defined in the test, `return_attention_scores=True`, "
            "`training=True`, and `use_causal_mask=True`. "
            "What is the exact execution order of function calls triggered by this "
            "test across `keras/src/layers/attention/grouped_query_attention.py`, "
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
