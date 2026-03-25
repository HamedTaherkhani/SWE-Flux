#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/_inline/inlinequery.py"
TARGET_FUNC = "telegram._inline.inlinequery.InlineQuery.answer"
TARGET_LINE = 183

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


def _decode_literal(raw: str) -> object:
    try:
        return ast.literal_eval(raw)
    except Exception:
        return raw


def extract_condition_snapshot(trace_text: str) -> dict[str, list[object]]:
    depth = 0
    call_snapshot: dict[str, object] = {}

    for line in trace_text.splitlines():
        m = EVENT_RE.match(line)
        if not m:
            continue

        path = m.group("path")
        func = m.group("func")
        event = m.group("event")
        lineno = int(m.group("lineno"))

        if path != TARGET_PATH or func != TARGET_FUNC:
            continue

        if event == "call":
            depth += 1
            if depth == 1:
                locals_map = _parse_locals(line)
                if "current_offset" in locals_map:
                    call_snapshot["current_offset"] = _decode_literal(locals_map["current_offset"])
                if "auto_pagination" in locals_map:
                    call_snapshot["auto_pagination"] = _decode_literal(locals_map["auto_pagination"])
            continue

        if event in {"return", "exception"}:
            depth = max(0, depth - 1)
            continue

        if event == "line" and depth == 1 and lineno == TARGET_LINE:
            return {
                "condition_values": [
                    call_snapshot.get("current_offset"),
                    call_snapshot.get("auto_pagination"),
                ]
            }

    raise ValueError("Target condition line was not observed in trace.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "inlinequery_answer_condition_snapshot/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "inlinequery_answer_condition_snapshot/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_condition_snapshot(trace_text)

    qa = {
        "question_kind": "conditional_statements",
        "question": (
            "Use `tests/qa/inlinequery_answer_condition_snapshot_test.py`, class "
            "`TestInlineQueryAnswerConditionSnapshotQA`, method "
            "`test_inlinequery_answer_condition_snapshot_case`. "
            "The test calls `inline_query.answer(...)` at line 77. "
            "In file `telegram/_inline/inlinequery.py`, function "
            "`telegram._inline.inlinequery.InlineQuery.answer`, at line `183` the condition is "
            "`if current_offset and auto_pagination:`. "
            "What were the exact values of `current_offset` and `auto_pagination` at that moment? "
            "Return a JSON object with key `condition_values` in this exact order: "
            "[`current_offset`, `auto_pagination`]."
        ),
        "template_answer": {
            "condition_values": ["str", "bool"],
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
