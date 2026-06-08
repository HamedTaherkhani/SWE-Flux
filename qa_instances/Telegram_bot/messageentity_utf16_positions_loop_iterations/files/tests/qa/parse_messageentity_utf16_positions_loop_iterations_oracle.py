#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/_messageentity.py"
TARGET_FUNC = "telegram._messageentity.MessageEntity.adjust_message_entities_to_utf_16"
# We count loop-body entries for `for i, position in enumerate(positions):` at line 203.
TARGET_BODY_LINE = 204

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)


def extract_iteration_count(trace_text: str) -> dict:
    count = 0
    for match in LINE_RE.finditer(trace_text):
        if (
            match.group("path") == TARGET_PATH
            and match.group("func") == TARGET_FUNC
            and int(match.group("lineno")) == TARGET_BODY_LINE
        ):
            count += 1

    return {"loop_iteration_count": count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/messageentity_utf16_positions_loop_iterations/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/messageentity_utf16_positions_loop_iterations/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_iteration_count(trace_text)

    qa = {
        "question_kind": "S3_Loops",
        "question": (
            "Use `tests/qa/messageentity_utf16_positions_loop_iterations_test.py`, class "
            "`TestMessageEntityUtf16PositionsLoopIterationsQA`, method "
            "`test_messageentity_utf16_positions_loop_iterations_case`. "
            "In file `telegram/_messageentity.py`, function "
            "`telegram._messageentity.MessageEntity.adjust_message_entities_to_utf_16`, consider "
            "the loop `for i, position in enumerate(positions):` at line `203` (body starts at "
            "line `204`). How many iterations does this loop execute during this test run? "
            "Return the answer as a JSON object with key `loop_iteration_count` and integer value."
        ),
        "template_answer": {
            "loop_iteration_count": "int"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
