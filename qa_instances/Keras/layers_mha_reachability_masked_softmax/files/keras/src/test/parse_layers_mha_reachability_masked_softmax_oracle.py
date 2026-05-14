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

TARGET_FUNCTION = "keras.src.layers.attention.multi_head_attention._masked_softmax"


def normalize_func_identifier(func: str) -> str:
    if "|||" in func:
        full_path, short_name = func.split("|||", 1)
        if short_name:
            return f"{full_path}|||{short_name}"
        func = full_path
    short_name = func.rsplit(".", 1)[-1]
    return f"{func}|||{short_name}"


def extract_calls(trace_text: str):
    calls = []
    for file_path, line_no, func in CALL_RE.findall(trace_text):
        calls.append(
            {
                "file": file_path.replace("/testbed/", ""),
                "line": int(line_no),
                "func": normalize_func_identifier(func),
            }
        )
    if not calls:
        raise ValueError("No call entries found in trace log.")
    return calls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/layers_mha_reachability_masked_softmax/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/layers_mha_reachability_masked_softmax/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    calls = extract_calls(trace_text)

    target_called = any(c["func"] == normalize_func_identifier(TARGET_FUNCTION) for c in calls)
    first_30_calls = calls[:30]

    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `keras/src/test/layers/attention/mha_reachability_masked_softmax_test.py`, "
            "class `MultiHeadAttentionReachabilityMaskedSoftmaxQATest`, method "
            "`test_masked_softmax_reachability_with_fast_path_conditions`. Setup: "
            "construct `MultiHeadAttention(num_heads=2, key_dim=2, value_dim=2, "
            "dropout=0.0, use_bias=True, seed=23)`, set query Keras mask to "
            "`[[True, True, False]]`, and call layer with explicit `query`, `value`, "
            "`key`, `value_mask=[[True, False, True, True]]`, "
            "`key_mask=[[True, True, False, True]]`, "
            "`attention_mask=[[[True, True, False, True], [True, False, False, True], "
            "[True, True, True, False]]]`, `return_attention_scores=False`, "
            "`training=True`, and `use_causal_mask=True`. "
            "In this specific test run, is function "
            "`keras.src.layers.attention.multi_head_attention._masked_softmax` ever called?"
        ),
        "oracle_answer": {
            "is_called": target_called
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
