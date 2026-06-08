#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

EXCEPTION_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/telegram/request/_baserequest\.py:(?P<lineno>\d+) "
    r"telegram\.request\._baserequest\.BaseRequest\._request_wrapper "
    r"event=exception exc=(?P<exc_type>[^:]+): (?P<exc_repr>.*?) locals=",
    re.MULTILINE,
)


def extract_exception_kind(trace_text: str) -> dict:
    matches = list(EXCEPTION_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find exception event for BaseRequest._request_wrapper.")

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
        default="/testbed/logs/qa_instances/baserequest_wrapper_exception_kind/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/baserequest_wrapper_exception_kind/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_exception_kind(trace_text)

    qa = {
        "question_kind": "S6_Exceptions",
        "question": (
            "Use `tests/qa/baserequest_wrapper_exception_kind_test.py`, class "
            "`TestBaseRequestWrapperExceptionKindQA`, method "
            "`test_baserequest_wrapper_exception_kind_case`. "
            "At line 68, `request.post(...)` is awaited, which enters "
            "`telegram/request/_baserequest.py:202` and then "
            "`telegram/request/_baserequest.py:287::BaseRequest._request_wrapper`. "
            "Inside `_request_wrapper`, this run reaches the `parameters` handling block "
            "(lines 363-369) and then raises an uncaught exception. "
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
