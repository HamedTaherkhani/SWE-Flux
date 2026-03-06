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

TARGET_FUNCTION = "keras.src.layers.attention.multi_head_attention._index_to_einsum_variable"


def extract_calls(trace_text: str):
    calls = []
    for file_path, line_no, func in CALL_RE.findall(trace_text):
        calls.append(
            {
                "file": file_path.replace("/testbed/", ""),
                "line": int(line_no),
                "func": func,
            }
        )
    if not calls:
        raise ValueError("No call events found in trace log.")
    return calls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/layers_mha_call_frequency_index_var/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/layers_mha_call_frequency_index_var/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    calls = extract_calls(trace_text)
    call_count = sum(1 for c in calls if c["func"] == TARGET_FUNCTION)

    qa = {
        "question_kind": "call_frequency",
        "question": (
            "Use `keras/src/test/layers/attention/mha_call_frequency_index_var_test.py`, "
            "class `MultiHeadAttentionCallFrequencyIndexVarQATest`, method "
            "`test_index_to_einsum_variable_call_frequency`. Setup: construct "
            "`MultiHeadAttention(num_heads=4, key_dim=2, value_dim=2, dropout=0.2, "
            "use_bias=True, seed=19)` and call it with the test `query` and `value`, "
            "`key=None`, explicit boolean `attention_mask` (as in the test), "
            "`return_attention_scores=True`, `training=True`, and "
            "`use_causal_mask=True`. "
            "In this test run, how many times is function "
            "`keras.src.layers.attention.multi_head_attention._index_to_einsum_variable` "
            "called?"
        ),
        "oracle_answer": {
            "target_function": TARGET_FUNCTION,
            "call_count": call_count,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
