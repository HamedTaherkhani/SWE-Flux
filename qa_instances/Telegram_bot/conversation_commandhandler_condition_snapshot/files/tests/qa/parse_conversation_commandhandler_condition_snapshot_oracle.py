#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/ext/_handlers/commandhandler.py"
TARGET_FUNC = "telegram.ext._handlers.commandhandler.CommandHandler.check_update"
TARGET_LINE = 196

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


def extract_condition_snapshot(trace_text: str) -> dict[str, list[str]]:
    depth = 0

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

        if event == "line" and depth == 1 and lineno == TARGET_LINE:
            locals_map = _parse_locals(line)
            if "command_parts" not in locals_map:
                raise ValueError("`command_parts` not found at target condition line.")

            command_parts = ast.literal_eval(locals_map["command_parts"])
            if not isinstance(command_parts, list) or len(command_parts) < 3:
                raise ValueError(f"Unexpected command_parts value: {command_parts!r}")

            left_value = str(command_parts[1]).lower()
            right_value = str(command_parts[2]).lower()

            return {
                "condition_values": [left_value, right_value],
            }

    raise ValueError("Target condition line was not observed in trace.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "conversation_commandhandler_condition_snapshot/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "conversation_commandhandler_condition_snapshot/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_condition_snapshot(trace_text)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `tests/qa/conversation_commandhandler_condition_snapshot_test.py`, class "
            "`TestConversationCommandHandlerConditionSnapshotQA`, method "
            "`test_conversation_commandhandler_condition_snapshot_case`. "
            "The test calls `conversation.check_update(update)` at line 68, and execution enters "
            "`telegram.ext._handlers.commandhandler.CommandHandler.check_update`. "
            "In file `telegram/ext/_handlers/commandhandler.py`, in the condition that starts at "
            "line `196` and continues at line `197`, the code checks "
            "`command_parts[1].lower() == message.get_bot().username.lower()`. "
            "What were the exact values of these two expressions at that evaluation point? "
            "Return a JSON object with key `condition_values` whose value is a two-element array "
            "in this exact order: "
            "[`command_parts[1].lower()`, `message.get_bot().username.lower()`]."
        ),
        "template_answer": {
            "condition_values": ["str", "str"],
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
