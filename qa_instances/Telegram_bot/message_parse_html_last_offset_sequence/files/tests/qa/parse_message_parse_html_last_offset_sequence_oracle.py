#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/_message.py"
TARGET_FUNC = "telegram._message.Message._parse_html"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _parse_locals(line: str) -> dict[str, str]:
    idx = line.find(" locals=")
    if idx == -1:
        return {}
    raw = line[idx + len(" locals=") :].strip()
    try:
        value = ast.literal_eval(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def extract_value_sequence(trace_text: str) -> dict:
    sequence: list[int] = []
    parse_html_stack: list[int | None] = []

    for line in trace_text.splitlines():
        m = EVENT_RE.match(line)
        if not m:
            continue

        path = m.group("path")
        func = m.group("func")
        event = m.group("event")

        if path != TARGET_PATH or func != TARGET_FUNC:
            continue

        locals_map = _parse_locals(line)

        if event == "call":
            offset_value = locals_map.get("offset")
            try:
                parse_html_stack.append(int(offset_value) if offset_value is not None else None)
            except ValueError:
                parse_html_stack.append(None)
            continue

        if event in {"return", "exception"}:
            if parse_html_stack:
                parse_html_stack.pop()
            continue

        if event == "line" and parse_html_stack and parse_html_stack[-1] == 0:
            if "last_offset" in locals_map:
                try:
                    sequence.append(int(locals_map["last_offset"]))
                except ValueError:
                    pass

    return {"value_sequence": sequence}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/message_parse_html_last_offset_sequence/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/message_parse_html_last_offset_sequence/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_value_sequence(trace_text)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `tests/qa/message_parse_html_last_offset_sequence_test.py`, class "
            "`TestMessageParseHtmlLastOffsetSequenceQA`, method "
            "`test_message_parse_html_last_offset_sequence_case`. "
            "The test executes `rendered = message.text_html_urled` at line 50, which calls "
            "`telegram._message.Message._parse_html` in `telegram/_message.py`. "
            "For the exact variable `last_offset` in that function, considering only the top-level "
            "invocation where argument `offset` is `0`, what is the ordered list of all values "
            "assigned to `last_offset` during this test run? "
            "Return the answer as `value_sequence`, a JSON array of integers in assignment order. "
            "In this function, assignments happen at line `4645` and line `4714`."
        ),
        "template_answer": {
            "value_sequence": []
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
