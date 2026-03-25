#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/_message.py"
TARGET_FUNC = "telegram._message.Message.compute_quote_position_and_entities"
TARGET_VAR = "position"
TARGET_ASSIGN_LINE = 1560

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _parse_locals(raw_line: str) -> dict[str, object]:
    marker = " locals="
    index = raw_line.find(marker)
    if index < 0:
        return {}
    raw_locals = raw_line[index + len(marker) :].strip()
    try:
        parsed = ast.literal_eval(raw_locals)
    except (ValueError, SyntaxError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _to_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if re.fullmatch(r"-?\d+", stripped):
            return int(stripped)
    return None


def extract_value_range(trace_text: str) -> dict[str, dict[str, int] | None]:
    observed: list[int] = []

    for raw_line in trace_text.splitlines():
        event_match = EVENT_RE.match(raw_line)
        if not event_match:
            continue
        if (
            event_match.group("path") != TARGET_PATH
            or event_match.group("func") != TARGET_FUNC
        ):
            continue

        locals_dict = _parse_locals(raw_line)
        if TARGET_VAR not in locals_dict:
            continue

        value = _to_int(locals_dict[TARGET_VAR])
        if value is not None:
            observed.append(value)

    if not observed:
        return {"position_range": None}

    return {
        "position_range": {
            "min": min(observed),
            "max": max(observed),
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "message_quote_position_value_range_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "message_quote_position_value_range_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_value_range(trace_text)

    qa = {
        "question_kind": "value_range_analysis",
        "question": (
            "Use the full test suite in `tests/qa/message_quote_position_value_range_suite_test.py` "
            "(all test methods in class `TestMessageQuotePositionValueRangeSuiteQA`, 12 tests). "
            "Focus on `telegram/_message.py`, function "
            "`telegram._message.Message.compute_quote_position_and_entities`, variable "
            "`position` assigned at line `1560` (`position = len(utf16_text[: "
            "matches[effective_index].start()]) // 2`). "
            "Across this full suite, what is the observed value range of `position`? "
            "Return JSON with key `position_range` using this schema: "
            "`{\"position_range\": {\"min\": <int>, \"max\": <int>}}`."
        ),
        "template_answer": {
            "position_range": {
                "min": "int",
                "max": "int"
            }
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
