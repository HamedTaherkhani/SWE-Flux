#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# The trace plugin records funcname as `<module>._collect_state` where the module
# name depends on how pytest imports the test file. Match by suffix only.
RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/test/qa/request_state_after_mutations_test\.py):(?P<lineno>\d+) "
    r"(?P<func>\S*\._collect_state) "
    r"event=return retval=(?P<retval>.*?) locals=\{.*\}$",
    re.MULTILINE,
)


def extract_snapshot(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No _collect_state return event in trace log.")
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly 1 _collect_state return event, got {len(matches)}.")
    retval_text = matches[0].group("retval")
    parsed = ast.literal_eval(retval_text)
    if not isinstance(parsed, dict):
        raise ValueError(f"Return value is not a dict: {parsed!r}")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/request_state_after_mutations/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/request_state_after_mutations/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    snapshot = extract_snapshot(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `test/qa/request_state_after_mutations_test.py`, class "
            "`TestRequestStateAfterMutationsQA`, method "
            "`test_request_state_after_mutations_case`. "
            "The test creates a single `yt_dlp.networking.common.Request` object (defined at "
            "line 385 in `yt_dlp/networking/common.py`) and then mutates it with this exact "
            "sequence of operations, in order: "
            "(1) construct `req = Request(url='HTTP://Example.COM/api?z=9&a=1', method='post', "
            "headers={'x-trace-ID': 'abc', 'Accept': 'application/json'}, data=b'hello', "
            "proxies={'http': 'http://proxy.local:8080'}, extensions={'timeout': 5})`; "
            "(2) call `req.update(url='https://example.com/v2/users', "
            "query={'limit': 10, 'page': 2}, "
            "headers={'X-TRACE-Id': 'def', 'x-new-header': '1'}, extensions={'retries': 3})`; "
            "(3) execute `req.data = None`; "
            "(4) execute `req.headers['accept-language'] = 'en-US'`. "
            "After all four steps, report the exact final state of the `req` object as a JSON "
            "object with seven keys: "
            "`url` (str, the value of `req.url`), "
            "`method` (str, the value of the `req.method` property), "
            "`data_repr` (str, the value of `repr(req.data)`, e.g. `None` or `b'...'`), "
            "`headers_titled` (object, equal to `dict(req.headers)` -- the case-insensitive "
            "store keyed by `str.title()` of each header name), "
            "`headers_sensitive` (object, equal to `req.headers.sensitive()` -- the "
            "original-case header names mapped to their values), "
            "`proxies` (object, equal to `dict(req.proxies)`), and "
            "`extensions` (object, equal to `dict(req.extensions)`). "
            "Header *values* must reflect any whitespace stripping and bytes-to-latin-1 "
            "decoding performed by `HTTPHeaderDict.__setitem__`. The dict insertion order "
            "for `headers_titled` and `headers_sensitive` must follow the actual final "
            "insertion order in the `Request`'s underlying dicts."
        ),
        "template_answer": {
            "url": "str",
            "method": "str",
            "data_repr": "str",
            "headers_titled": {"str": "str"},
            "headers_sensitive": {"str": "str"},
            "proxies": {"str": "str"},
            "extensions": {"str": "int_or_str"},
        },
        "oracle_answer": snapshot,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
