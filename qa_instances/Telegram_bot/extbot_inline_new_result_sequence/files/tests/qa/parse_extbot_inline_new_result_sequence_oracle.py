#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/ext/_extbot.py"
TARGET_FUNC = "telegram.ext._extbot.ExtBot._effective_inline_results"
TARGET_ASSIGN_LINE = 702

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
    sequence: list[str] = []
    prev_lineno_for_func: int | None = None

    for line in trace_text.splitlines():
        m = EVENT_RE.match(line)
        if not m:
            continue

        path = m.group("path")
        func = m.group("func")
        event = m.group("event")
        lineno = int(m.group("lineno"))

        if path != TARGET_PATH or func != TARGET_FUNC or event != "line":
            continue

        if lineno != TARGET_ASSIGN_LINE + 1:
            prev_lineno_for_func = lineno
            continue

        locals_map = _parse_locals(line)
        # Capture only the immediate post-assignment state of
        # `new_result = copy(result)` (line 702 -> line 703 transition).
        if "new_result" in locals_map and prev_lineno_for_func == TARGET_ASSIGN_LINE:
            sequence.append(locals_map["new_result"])
        prev_lineno_for_func = lineno

    return {"value_sequence": sequence}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/extbot_inline_new_result_sequence/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/extbot_inline_new_result_sequence/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_value_sequence(trace_text)

    qa = {
        "question_kind": "temporal_value_history_sequence",
        "question": (
            "Use `tests/qa/extbot_inline_new_result_sequence_test.py`, class "
            "`TestExtBotInlineNewResultSequenceQA`, method "
            "`test_extbot_inline_new_result_sequence_case`. "
            "The test executes `bot._effective_inline_results(...)` at line 60. "
            "In file `telegram/ext/_extbot.py`, function "
            "`telegram.ext._extbot.ExtBot._effective_inline_results`, track the exact variable "
            "`new_result` assigned at line `702` (`new_result = copy(result)`). "
            "What is the ordered list of all values assigned to `new_result` during this test run? "
            "Return the answer as `value_sequence`, a JSON array of strings in assignment order."
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
