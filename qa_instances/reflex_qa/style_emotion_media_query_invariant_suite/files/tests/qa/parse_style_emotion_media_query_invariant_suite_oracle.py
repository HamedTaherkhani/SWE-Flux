#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_FILE = Path("/testbed/reflex/style.py")
TARGET_FUNC = "reflex.style.format_as_emotion"
TARGET_LINE = 373

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/reflex/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) (?P<rest>.*)$",
    re.MULTILINE,
)


def parse_locals(rest: str) -> dict[str, str]:
    if "locals=" not in rest:
        return {}
    try:
        parsed = ast.literal_eval(rest.split("locals=", 1)[1])
    except (SyntaxError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def extract_values(trace_text: str) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    frames: list[dict[str, str]] = []
    for match in TRACE_RE.finditer(trace_text):
        if match.group("path") != str(TARGET_FILE) or match.group("func") != TARGET_FUNC:
            continue
        event = match.group("event")
        locals_delta = parse_locals(match.group("rest"))
        if event == "call":
            frames.append(dict(locals_delta))
            continue
        if not frames:
            continue
        if event in {"return", "exception"}:
            frames.pop()
            continue
        frames[-1].update(locals_delta)
        if int(match.group("lineno")) == TARGET_LINE:
            frame = frames[-1]
            mq = ast.literal_eval(frame["mq"])
            emotion_style_repr = frame.get("emotion_style", "{}")
            values.append((mq, emotion_style_repr))
    if not values:
        raise ValueError("No target evaluations observed.")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default="/testbed/logs/qa_instances/style_emotion_media_query_invariant_suite/trace.log")
    parser.add_argument("--out", default="/testbed/logs/qa_instances/style_emotion_media_query_invariant_suite/oracle.json")
    args = parser.parse_args()
    values = extract_values(Path(args.trace_log).read_text(encoding="utf-8"))
    invariant_exists = all(mq not in emotion_style_repr for mq, emotion_style_repr in values)
    qa = {
        "question_kind": "M7_Invariants",
        "question": (
            "Use the full test suite in `tests/qa/style_emotion_media_query_invariant_suite_test.py` "
            "(all 10 test classes). Focus on `reflex/style.py`, function "
            "`reflex.style.format_as_emotion`, lines 338-382. At line 373 "
            "(`emotion_style.setdefault(mq, {}).update(style_sub_dict)`), consider local variable "
            "`mq` and local variable `emotion_style` immediately before this update executes. Across "
            "all evaluations of this line over the full suite, is the relationship "
            "`mq not in emotion_style` an invariant property? Return JSON as "
            "`{\\\"invariant_exists\\\": <bool>}` where `true` means the relationship holds for "
            "every evaluation and `false` means it does not hold."
        ),
        "template_answer": {"invariant_exists": "bool"},
        "oracle_answer": {"invariant_exists": invariant_exists},
    }
    Path(args.out).write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
