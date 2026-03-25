#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/_message\.py):(?P<lineno>\d+) "
    r"(?P<func>telegram\._message\.Message\._parse_markdown) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _count_entities(sorted_entities_repr: str) -> int:
    return len(re.findall(r"MessageEntity\(", sorted_entities_repr))


def extract_loop_state(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find Message._parse_markdown return events in trace log.")

    best_locals = None
    best_count = -1
    for match in matches:
        locals_dict = ast.literal_eval(match.group("locals"))
        sorted_entities_repr = locals_dict.get("sorted_entities", "")
        count = _count_entities(sorted_entities_repr)
        if count > best_count:
            best_count = count
            best_locals = locals_dict

    if best_locals is None:
        raise ValueError("Could not identify outer _parse_markdown call from trace log.")

    markdown_text = ast.literal_eval(best_locals["markdown_text"])

    return {
        "markdown_text": markdown_text,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/chatmemberupdated_difference_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/chatmemberupdated_difference_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_loop_state(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/chatmemberupdated_difference_state_test.py`, class "
            "`TestChatMemberUpdatedDifferenceStateQA`, method "
            "`test_loop_conditional_markdown_state_case`. "
            "At line 60, variable `markdown_v2` is assigned from "
            "`message_obj.text_markdown_v2`, which calls "
            "`telegram/_message.py:4822::Message._parse_markdown` with Markdown version 2. "
            "Inside `_parse_markdown`, a loop over `sorted_entities` runs at line 4853, "
            "conditional skip `if entity in parsed_entities` is evaluated at lines 4854-4855, "
            "`parsed_entities` is updated at line 4864, and `last_offset` is updated at line 4946. "
            "What is the exact full value of variable `markdown_text` at function return line 4954 "
            "for the outer call (i.e., after the loop and conditional branches have executed)? "
            "Return exactly: `markdown_text`."
        ),
        "template_answer": {
            "markdown_text": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
