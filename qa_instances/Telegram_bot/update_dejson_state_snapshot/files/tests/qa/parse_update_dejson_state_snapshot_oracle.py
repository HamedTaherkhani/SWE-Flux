#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


TO_DICT_RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/_telegramobject\.py):(?P<lineno>\d+) "
    r"(?P<func>telegram\._telegramobject\.TelegramObject\.to_dict) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

ENUM_TOKEN_RE = re.compile(r"<[A-Za-z_][A-Za-z0-9_]*\.([A-Za-z_][A-Za-z0-9_]*)>")


def _normalize_enum_tokens(payload: str) -> str:
    return ENUM_TOKEN_RE.sub(r"'\1'", payload)


def extract_update_state(trace_text: str) -> dict:
    matches = list(TO_DICT_RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find TelegramObject.to_dict return events in trace log.")

    target = None
    for match in matches:
        locals_blob = match.group("locals")
        if re.search(r"'self': [\"']Update\(", locals_blob):
            target = match
    if target is None:
        raise ValueError("Could not find top-level Update.to_dict return event in trace log.")

    retval = _normalize_enum_tokens(target.group("retval"))
    update_dict = ast.literal_eval(retval)
    if not isinstance(update_dict, dict):
        raise ValueError("Parsed Update.to_dict return value is not a dict.")

    return {
        "state_dict": update_dict,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/update_dejson_state_snapshot/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/update_dejson_state_snapshot/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    snapshot = extract_update_state(trace_text)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `tests/qa/update_dejson_state_snapshot_test.py`, class "
            "`TestUpdateDejsonStateSnapshotQA`, method `test_update_dejson_state_snapshot_case`. "
            "At line 76, variable `update_obj` is assigned from "
            "`telegram/_update.py:761::Update.de_json(raw_update, None)`. "
            "At line 77, variable `state_dict` is assigned from "
            "`telegram/_telegramobject.py:582::TelegramObject.to_dict()` called on that same "
            "`update_obj`. What is the exact value of variable `state_dict` at line 77?"
        ),
        "template_answer": {
            "state_dict": "dict[str, object]",
        },
        "oracle_answer": snapshot,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
