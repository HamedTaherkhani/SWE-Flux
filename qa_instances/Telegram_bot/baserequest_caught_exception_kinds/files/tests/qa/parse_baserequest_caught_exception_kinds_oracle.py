#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXCEPTION_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/telegram/request/_baserequest\.py:(?P<lineno>\d+) "
    r"telegram\.request\._baserequest\.BaseRequest\._request_wrapper "
    r"event=exception exc=(?P<exc_type>[^:]+):",
    re.MULTILINE,
)


# These exceptions are thrown by do_request and handled by _request_wrapper except clauses.
CAUGHT_CANDIDATES = {"InvalidToken", "RuntimeError", "TelegramError", "TimeoutError"}


def extract_caught_exception_kinds(trace_text: str) -> dict:
    matches = list(EXCEPTION_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find exception events for BaseRequest._request_wrapper.")

    caught_types = []
    seen = set()
    for match in matches:
        lineno = int(match.group("lineno"))
        exc_type = match.group("exc_type").strip()

        if lineno == 334 and exc_type in CAUGHT_CANDIDATES and exc_type not in seen:
            seen.add(exc_type)
            caught_types.append(exc_type)

    if not caught_types:
        raise ValueError("Could not extract caught exception kinds from trace.")

    return {"caught_exception_kinds": caught_types}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/baserequest_caught_exception_kinds/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/baserequest_caught_exception_kinds/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_caught_exception_kinds(trace_text)

    qa = {
        "question_kind": "abnormal_behavior_prediction",
        "question": (
            "Use `tests/qa/baserequest_caught_exception_kinds_test.py`, class "
            "`TestBaseRequestCaughtExceptionKindsQA`, method "
            "`test_baserequest_caught_exception_kinds_case`. "
            "During the two `request.post(...)` calls inside the loop at lines 54-57, execution enters "
            "`telegram/request/_baserequest.py:287::BaseRequest._request_wrapper`. "
            "At line 334 (`code, payload = await self.do_request(...)`), exceptions are raised from "
            "`do_request` and caught by `_request_wrapper` except clauses (`except TelegramError` and "
            "`except Exception`). What are the exact exception kinds that are caught during this test "
            "execution, in first-seen order?"
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
