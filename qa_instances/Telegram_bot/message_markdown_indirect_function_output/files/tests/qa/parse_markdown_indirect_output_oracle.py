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


def extract_output(trace_text: str) -> str:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find _parse_markdown return events in trace log.")

    target = None
    for match in matches:
        locals_text = match.group("locals")
        if (
            "'version': '2'" in locals_text
            and "'offset': '0'" in locals_text
            and "'urled': 'True'" in locals_text
        ):
            target = match
    if target is None:
        raise ValueError("Could not find top-level _parse_markdown return event in trace log.")

    retval = target.group("retval")
    parsed = ast.literal_eval(retval)
    if not isinstance(parsed, str):
        raise ValueError("Parsed return value is not a string.")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/message_markdown_indirect_function_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/message_markdown_indirect_function_output/oracle.json",
    )
    args = parser.parse_args()

    trace_log = Path(args.trace_log).read_text(encoding="utf-8")
    markdown_text = extract_output(trace_log)

    qa = {
        "question_kind": "function_output_indirect",
        "question": (
            "Use `tests/qa/markdown_indirect_output_case_test.py`, class "
            "`TestMarkdownIndirectOutputQA`, method `test_markdown_v2_indirect_target_output_case`. "
            "The method builds a `Message` with ASCII text "
            "`start bold and italic end plus http://example.com/a_b and code x_y` and entities "
            "`BOLD(6,15)`, `ITALIC(15,6)`, `URL(31,22)`, `CODE(63,3)`, then accesses "
            "`message.text_markdown_v2_urled` at `telegram/_message.py:5067`. "
            "That property calls `Message._parse_markdown` (`telegram/_message.py:4822`). "
            "Inside `_parse_markdown`, the variable `markdown_text` is accumulated and returned at "
            "`telegram/_message.py:4954`. For the top-level call where `version == 2`, "
            "`urled is True`, and `offset == 0`, what is the exact returned string at line 4954?"
        ),
        "template_answer": {"markdown_text": "str"},
        "oracle_answer": {"markdown_text": markdown_text},
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
