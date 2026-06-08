#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/_telegramobject\.py):(?P<lineno>\d+) "
    r"(?P<func>telegram\._telegramobject\.TelegramObject\._de_json) "
    r"event=call locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

def extract_input_state(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find TelegramObject._de_json call events in trace log.")

    target_locals = None
    for match in matches:
        locals_dict = ast.literal_eval(match.group("locals"))
        if locals_dict.get("cls") == "<class 'telegram._chatmember.ChatMemberRestricted'>":
            target_locals = locals_dict
            break

    if target_locals is None:
        raise ValueError("Could not find _de_json call with cls=ChatMemberRestricted.")

    return {
        "cls": target_locals["cls"],
        "api_kwargs": ast.literal_eval(target_locals["api_kwargs"]),
        "data": target_locals["data"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/chatmember_restricted_indirect_input_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/chatmember_restricted_indirect_input_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    input_state = extract_input_state(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/chatmember_restricted_indirect_input_state_test.py`, class "
            "`TestChatMemberRestrictedIndirectInputStateQA`, method "
            "`test_chatmember_restricted_indirect_input_state_case`. "
            "At line 61, variable `parsed_member` is assigned by calling "
            "`telegram/_chatmember.py:110::ChatMember.de_json(raw_member, bot)`. "
            "During that execution path, `telegram/_chatmember.py:137` calls "
            "`telegram/_telegramobject.py:388::TelegramObject._de_json(data=data, bot=bot, "
            "api_kwargs=api_kwargs)` for the `ChatMemberRestricted` branch. "
            "What are the exact values of input variables `cls`, `api_kwargs`, and `data` "
            "at entry of that `_de_json` call?"
        ),
        "template_answer": {
            "cls": "str",
            "api_kwargs": "dict[str, bool]",
            "data": "str",
        },
        "oracle_answer": input_state,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
