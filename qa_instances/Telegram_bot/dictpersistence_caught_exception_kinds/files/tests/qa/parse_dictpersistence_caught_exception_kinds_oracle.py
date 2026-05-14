#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXCEPTION_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/telegram/ext/_dictpersistence\.py:(?P<lineno>\d+) "
    r"telegram\.ext\._dictpersistence\.DictPersistence\.__init__ "
    r"event=exception exc=(?P<exc_type>[^:]+):",
    re.MULTILINE,
)

# Caught internally by __init__ at except blocks (e.g. lines 152 etc.).
CAUGHT_CANDIDATES = {"ValueError", "IndexError", "AttributeError"}


def extract_caught_exception_kinds(trace_text: str) -> dict:
    matches = list(EXCEPTION_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find exception events for DictPersistence.__init__.")

    caught_types = []
    seen = set()
    for match in matches:
        exc_type = match.group("exc_type").strip()
        if exc_type in CAUGHT_CANDIDATES and exc_type not in seen:
            seen.add(exc_type)
            caught_types.append(exc_type)

    if not caught_types:
        raise ValueError("Could not extract caught exception kinds from trace.")

    return {"caught_exception_kinds": caught_types}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/dictpersistence_caught_exception_kinds/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/dictpersistence_caught_exception_kinds/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_caught_exception_kinds(trace_text)

    qa = {
        "question_kind": "C6_Exceptions",
        "question": (
            "Use `tests/qa/dictpersistence_caught_exception_kinds_test.py`, class "
            "`TestDictPersistenceCaughtExceptionKindsQA`, method "
            "`test_dictpersistence_caught_exception_kinds_case`. "
            "The loop at lines 30-33 calls `DictPersistence(callback_data_json=raw_callback_json)` "
            "twice. This enters `telegram/ext/_dictpersistence.py:93::DictPersistence.__init__`. "
            "In `__init__`, the callback data parsing/shape block (lines 143-153) catches "
            "exceptions and re-raises a `TypeError`. What are the exact kinds of exceptions that "
            "are caught internally during this test execution, in first-seen order?"
        ),
        "template_answer": {
            "caught_exception_kinds": ["str"],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
