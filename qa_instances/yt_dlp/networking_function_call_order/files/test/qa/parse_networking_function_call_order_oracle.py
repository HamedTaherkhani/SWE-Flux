#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_call_order(trace_text: str) -> dict[str, object]:
    called_funcs: list[str] = []
    for m in CALL_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith("yt_dlp/utils/networking.py"):
            continue
        called_funcs.append(m.group("func"))
    if not called_funcs:
        raise ValueError("No call events found for yt_dlp/utils/networking.py in trace.")
    return {"called_funcs": called_funcs}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/networking_function_call_order/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/networking_function_call_order/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_call_order(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/networking_function_call_order_test.py`, class "
            "`TestNetworkingFunctionCallOrderQA`, method "
            "`test_networking_function_call_order_case`. Collect only the trace lines "
            "where `event=call` and `path` ends with `yt_dlp/utils/networking.py`. What is the "
            "exact execution order of the `func` values in those lines (including repeats), "
            "from first to last? Return them as `called_funcs`."
        ),
        "template_answer": {
            "called_funcs": ["str"],
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
