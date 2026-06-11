#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/_message\.py):(?P<lineno>\d+) "
    r"(?P<func>telegram\._message\.Message\._parse_html) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _count_entities(sorted_entities_repr: str) -> int:
    return len(re.findall(r"MessageEntity\(", sorted_entities_repr))


def extract_state(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find Message._parse_html return events in trace log.")

    target_locals = None
    target_count = -1
    for match in matches:
        locals_dict = ast.literal_eval(match.group("locals"))
        count = _count_entities(locals_dict.get("sorted_entities", ""))
        if count > target_count:
            target_count = count
            target_locals = locals_dict

    if target_locals is None:
        raise ValueError("Could not identify outer _parse_html call from trace log.")

    escaped_text = ast.literal_eval(target_locals["escaped_text"])
    insert_value = ast.literal_eval(target_locals["insert"])
    html_text_value = ast.literal_eval(target_locals["html_text"])

    return {
        "escaped_text": escaped_text,
        "insert": insert_value,
        "html_text": html_text_value,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/callbackquery_dejson_postcall_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/callbackquery_dejson_postcall_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_state(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/callbackquery_dejson_postcall_state_test.py`, class "
            "`TestCallbackQueryPostCallStateQA`, method "
            "`test_parse_html_postcall_state_case`. "
            "At line 28, `html_urled = message.text_html_urled` calls "
            "`telegram/_message.py:4633::Message._parse_html`. In the outer `_parse_html` call, "
            "the URL entity branch executes `escaped_text = escape(text)` at line 4668 and then "
            "sets `insert` at line 4675. At return line 4719, `html_text` is returned. "
            "What are the exact values of variables `escaped_text` (line 4668), "
            "`insert` (line 4675), and `html_text` (line 4719) for that outer call? "
            "Return exactly: `escaped_text`, `insert`, `html_text`."
        ),
        "template_answer": {
            "escaped_text": "str",
            "insert": "str",
            "html_text": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
