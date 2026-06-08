#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/ext/_handlers/conversationhandler.py"
TARGET_FUNC = "telegram.ext._handlers.conversationhandler.ConversationHandler.check_update"
LOOP_BODY_LINE = 780

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def count_loop_iterations(trace_text: str) -> int:
    depth = 0
    count = 0

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
            count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "conversationhandler_state_candidates_loop_iterations/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "conversationhandler_state_candidates_loop_iterations/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    iteration_count = count_loop_iterations(trace_text)

    qa = {
        "question_kind": "S3_Loops",
        "question": (
            "Use `tests/qa/conversationhandler_state_candidates_loop_iterations_test.py`, class "
            "`TestConversationHandlerStateCandidatesLoopIterationsQA`, method "
            "`test_conversationhandler_state_candidates_loop_iterations_case`. "
            "The test calls `conversation.check_update(update)` at line 65. "
            "In file `telegram/ext/_handlers/conversationhandler.py`, function "
            "`telegram.ext._handlers.conversationhandler.ConversationHandler.check_update`, "
            "consider the loop `for candidate in self.states.get(state, []):` at line `779` "
            "(body starts at line `780`). "
            "How many iterations does this loop execute during this test run? "
            "Return a JSON object with key `loop_iteration_count` and integer value."
        ),
        "template_answer": {
            "loop_iteration_count": "int",
        },
        "oracle_answer": {
            "loop_iteration_count": iteration_count,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
