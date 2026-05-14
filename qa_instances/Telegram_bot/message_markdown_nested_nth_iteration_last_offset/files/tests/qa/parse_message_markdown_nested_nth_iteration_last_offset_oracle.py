#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/_message.py"
TARGET_FUNC = "telegram._message.Message._parse_markdown"
LOOP_BODY_LINE = 4854
NTH = 8
VARIABLE = "entity"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)
ENTITY_RE = re.compile(
    r"MessageEntity\("
    r"(?=.*\blength=(?P<length>\d+))"
    r"(?=.*\boffset=(?P<offset>\d+))"
    r"(?=.*\btype=<MessageEntityType\.(?P<etype>[A-Z_]+)>)"
    r".*\)$"
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


def _decode_value(raw: str) -> object:
    try:
        return ast.literal_eval(raw)
    except Exception:
        return raw


def _entity_to_dict(raw: str) -> dict[str, object]:
    decoded = _decode_value(raw)
    if not isinstance(decoded, str):
        raise ValueError(f"Expected entity as string repr, got: {type(decoded).__name__}")

    m = ENTITY_RE.match(decoded)
    if not m:
        raise ValueError(f"Could not parse MessageEntity repr: {decoded}")

    return {
        "type": f"MessageEntityType.{m.group('etype')}",
        "offset": int(m.group("offset")),
        "length": int(m.group("length")),
    }


def extract_nth_iteration_value(trace_text: str) -> dict[str, object]:
    depth = 0
    iteration = 0

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
            continue

        if event in {"return", "exception"}:
            depth = max(0, depth - 1)
            continue

        if event == "line" and depth == 1 and lineno == LOOP_BODY_LINE:
            iteration += 1
            if iteration == NTH:
                locals_map = _parse_locals(line)
                if VARIABLE not in locals_map:
                    raise ValueError(
                        f"Variable '{VARIABLE}' missing at iteration {NTH} in target loop."
                    )

                return {
                    "nth_iteration": NTH,
                    "variable": VARIABLE,
                    "value": _entity_to_dict(locals_map[VARIABLE]),
                }

    raise ValueError(f"Could not observe iteration {NTH} in top-level target loop.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "message_markdown_nested_nth_iteration_last_offset/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "message_markdown_nested_nth_iteration_last_offset/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_nth_iteration_value(trace_text)

    qa = {
        "question_kind": "C3_Loops",
        "question": (
            "Use `tests/qa/message_markdown_nested_nth_iteration_last_offset_test.py`, class "
            "`TestMessageMarkdownNestedNthIterationLastOffsetQA`, method "
            "`test_message_markdown_nested_nth_iteration_last_offset_case`. "
            "The test evaluates `message.text_markdown_v2` at line 67, which calls "
            "`telegram._message.Message._parse_markdown`. "
            "In file `telegram/_message.py`, function "
            "`telegram._message.Message._parse_markdown`, consider the loop "
            "`for entity, text in sorted_entities:` at line `4853` (body starts at line `4854`). "
            "At the start of the 8th iteration of this loop in the top-level invocation "
            "(`offset == 0`), what is the exact value of variable `entity` "
            "(bound by the loop at line `4853`)? "
            "Return a JSON object with exactly keys: `nth_iteration`, `variable`, `value`. "
            "For `value`, return an object with exactly keys: `type`, `offset`, `length`."
        ),
        "template_answer": {
            "nth_iteration": "int",
            "variable": "str",
            "value": {
                "type": "str",
                "offset": "int",
                "length": "int",
            },
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
