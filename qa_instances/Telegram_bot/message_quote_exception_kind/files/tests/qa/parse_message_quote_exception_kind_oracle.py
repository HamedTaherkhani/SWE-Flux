#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

EXCEPTION_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/telegram/_message\.py:(?P<lineno>\d+) "
    r"telegram\._message\.Message\.compute_quote_position_and_entities "
    r"event=exception exc=(?P<exc_type>[^:]+): (?P<exc_repr>.*?) locals=",
    re.MULTILINE,
)


def extract_exception_kind(trace_text: str) -> dict:
    matches = list(EXCEPTION_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find exception event for Message.compute_quote_position_and_entities.")

    match = matches[-1]
    exc_type = match.group("exc_type").strip()
    exc_repr = match.group("exc_repr").strip()

    exc_message = exc_repr
    prefix = f"{exc_type}("
    if exc_repr.startswith(prefix) and exc_repr.endswith(")"):
        inner = exc_repr[len(prefix) : -1]
        try:
            exc_message = str(ast.literal_eval(inner))
        except Exception:
            exc_message = inner

    return {"exception_type": exc_type, "exception_message": exc_message}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/message_quote_exception_kind/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/message_quote_exception_kind/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_exception_kind(trace_text)

    qa = {
        "question_kind": "exception_uncaught_kind",
        "question": (
            "Use `tests/qa/message_quote_exception_kind_test.py`, class "
            "`TestMessageQuoteExceptionKindQA`, method `test_message_quote_exception_kind_case`. "
            "At line 26, `message.build_reply_arguments(...)` is called with `quote=selected_quote` "
            "and `quote_index=quote_index`, which indirectly calls "
            "`telegram/_message.py:1510::Message.compute_quote_position_and_entities`. "
            "At line 1555 of that function, an uncaught exception is raised on this execution path. "
            "What are the exact exception type and exception message?"
        ),
        "template_answer": {
            "exception_type": "str",
            "exception_message": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
