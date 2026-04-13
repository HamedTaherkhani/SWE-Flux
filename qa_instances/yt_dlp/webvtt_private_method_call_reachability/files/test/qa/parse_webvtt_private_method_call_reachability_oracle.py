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


def extract_answer(trace_text: str) -> dict[str, object]:
    # In this benchmark image, the tracer records the private helper as
    # `yt_dlp.webvtt.__parse_tsmap` (not `Magic._Magic__parse_tsmap`).
    target_func = "yt_dlp.webvtt.__parse_tsmap"
    for m in CALL_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith("yt_dlp/webvtt.py"):
            continue
        func = m.group("func")
        if func == target_func:
            return {"is_called": True}
    return {"is_called": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/webvtt_private_method_call_reachability/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/webvtt_private_method_call_reachability/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_answer(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/webvtt_private_method_call_reachability_test.py`, class "
            "`TestWebvttPrivateMethodCallReachabilityQA`, method "
            "`test_webvtt_private_method_call_reachability_case`. In `yt_dlp/webvtt.py`, "
            "the parser calls a private helper `__parse_tsmap` (emitted in the trace as the "
            "`func` value `yt_dlp.webvtt.__parse_tsmap`). Is `yt_dlp.webvtt.__parse_tsmap` ever "
            "called during the test? Return `is_called` as a boolean."
        ),
        "template_answer": {"is_called": "bool"},
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
