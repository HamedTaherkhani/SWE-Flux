#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/_message\.py):(?P<lineno>\d+) "
    r"(?P<func>telegram\._message\.Message\.compute_quote_position_and_entities) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_size(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find compute_quote_position_and_entities return events.")

    target_locals = None
    for match in matches:
        locals_dict = ast.literal_eval(match.group("locals"))
        quote_value = ast.literal_eval(locals_dict.get("quote", "''"))
        index_value = ast.literal_eval(locals_dict.get("index", "None"))
        if quote_value == "beta gamma" and index_value == 0:
            target_locals = locals_dict
            break

    if target_locals is None:
        raise ValueError("Could not find target compute_quote_position_and_entities call.")

    entities_repr = target_locals["entities"]
    size_value = len(re.findall(r"MessageEntity\(", entities_repr))

    return {
        "entities": size_value,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/message_quote_entities_size/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/message_quote_entities_size/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_size(trace_text)

    qa = {
        "question_kind": "variable_shape_size",
        "question": (
            "Use `tests/qa/message_quote_entities_size_test.py`, class "
            "`TestMessageQuoteEntitiesSizeQA`, method `test_quote_entities_size_case`. "
            "At line 57, variable `reply_kwargs` is assigned from "
            "`message.build_reply_arguments(...)`, which indirectly calls "
            "`telegram/_message.py:1510::Message.compute_quote_position_and_entities` with "
            "`quote='beta gamma'` and `index=0` (passed as `target_index` from line 13). "
            "Inside that function, variable `entities` is initialized at line 1564 and appended in "
            "the loop through line 1582. At return line 1584, what is the size of variable "
            "`entities`?"
        ),
        "template_answer": {
            "entities": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
