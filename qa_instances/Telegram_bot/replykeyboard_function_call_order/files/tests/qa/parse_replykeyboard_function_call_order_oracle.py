#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)

TRACED_FUNCS = (
    "telegram._webappinfo.WebAppInfo.__init__",
    "telegram._keyboardbutton.KeyboardButton.__init__",
    "telegram._replykeyboardmarkup.ReplyKeyboardMarkup.__init__",
    "telegram._utils.markup.check_keyboard_type",
    "telegram._telegramobject.TelegramObject.to_dict",
    "telegram._telegramobject.TelegramObject._get_attrs",
    "telegram._telegramobject.TelegramObject._get_attrs_names",
)


def extract_call_order(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find call events for function-call order extraction.")

    function_call_order = []
    for match in matches:
        func_name = match.group("func")
        if "<locals>" in func_name:
            continue
        if func_name not in TRACED_FUNCS:
            continue

        function_call_order.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": func_name,
            }
        )

    return {"function_call_order": function_call_order}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/replykeyboard_function_call_order/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/replykeyboard_function_call_order/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_order(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `tests/qa/replykeyboard_function_call_order_test.py`, class "
            "`TestReplyKeyboardFunctionCallOrderQA`, method "
            "`test_replykeyboard_function_call_order_case`. "
            "At line 23, `markup_dict = markup.to_dict()` is executed after constructing a "
            "`ReplyKeyboardMarkup` with mixed button types. "
            "For this instance, consider only traced `event=call` entries for these exact "
            "qualified functions: "
            "`telegram._webappinfo.WebAppInfo.__init__`, "
            "`telegram._keyboardbutton.KeyboardButton.__init__`, "
            "`telegram._replykeyboardmarkup.ReplyKeyboardMarkup.__init__`, "
            "`telegram._utils.markup.check_keyboard_type`, "
            "`telegram._telegramobject.TelegramObject.to_dict`, "
            "`telegram._telegramobject.TelegramObject._get_attrs`, and "
            "`telegram._telegramobject.TelegramObject._get_attrs_names`. "
            "Exclude any traced call whose qualified function name contains `<locals>` "
            "(for example generator or comprehension frames). "
            "What is the exact ordered sequence of those traced function calls during this "
            "test run, as a list of objects with keys `file` and `func`, including repeated calls?"
        ),
        "template_answer": {
            "function_call_order": [
                {
                    "file": "str",
                    "func": "str",
                }
            ]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
