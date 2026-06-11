#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/_telegramobject\.py):(?P<lineno>\d+) "
    r"(?P<func>telegram\._telegramobject\.TelegramObject\._get_attrs) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _parse_data_dict(data_repr: str) -> dict:
    normalized = re.sub(r"<[A-Za-z_][A-Za-z0-9_]*\.([A-Za-z_][A-Za-z0-9_]*)>", r"'\1'", data_repr)
    normalized = re.sub(r"mappingproxy\((\{.*?\})\)", r"\1", normalized)

    parsed = ast.literal_eval(normalized)
    if not isinstance(parsed, dict):
        raise ValueError("Parsed `data` is not a dictionary.")
    return parsed


def extract_keys_state(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find TelegramObject._get_attrs return events in trace log.")

    target_locals = None
    for match in matches:
        locals_dict = ast.literal_eval(match.group("locals"))
        if "CallbackQuery(" in locals_dict.get("self", "") and locals_dict.get("recursive") == "True":
            target_locals = locals_dict
            break

    if target_locals is None:
        raise ValueError("Could not find outer _get_attrs return event for CallbackQuery.")

    data_repr = target_locals["data"]
    parsed_data = _parse_data_dict(data_repr)

    return {
        "data": parsed_data,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/chatmember_restricted_data_keys/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/chatmember_restricted_data_keys/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_keys_state(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/chatmember_restricted_data_keys_test.py`, class "
            "`TestChatMemberRestrictedDataKeysQA`, method "
            "`test_telegramobject_get_attrs_data_keys_case`. "
            "At line 34, variable `attrs_map` is assigned from "
            "`callback_query._get_attrs(recursive=True, include_private=False, remove_bot=False)`, "
            "which executes `telegram/_telegramobject.py:526::TelegramObject._get_attrs`. "
            "Inside `_get_attrs`, variable `data` is populated in the loop at lines 550-563 and "
            "then conditionally rewritten by `if recursive and data.get('from_user')` at lines "
            "565-566. At return line 569, what is the exact dictionary value of variable `data` "
            "in that outer `CallbackQuery` call? Return exactly: `data` with all keys and values."
        ),
        "template_answer": {
            "data": "dict[str, object]",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
