#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/libqtile/backend/x11/window\.py:(?P<lineno>\d+) "
    r"(?P<func>libqtile\.backend\.x11\.window\.(?:XWindow\.)?set_property) "
    r"event=exception exc=(?P<exc>[^:]+): ",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    seen = []
    for m in EXC_RE.finditer(trace_text):
        kind = m.group("exc").strip()
        if kind not in seen:
            seen.append(kind)

    if not seen:
        raise ValueError("Could not find exception events for XWindow.set_property in trace log.")

    return {"caught_exception_kinds": seen}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "backend_x11_window_direct_set_property_caught_exception_kinds/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "backend_x11_window_direct_set_property_caught_exception_kinds/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S6_Exceptions",
        "question": (
            "Use `tests/qa/backend_x11_window_direct_set_property_caught_exception_kinds_test.py`, "
            "class `TestBackendX11WindowDirectSetPropertyCaughtExceptionKindsQA`, method "
            "`test_backend_x11_window_direct_set_property_caught_exception_kinds_case`. "
            "This is a direct backend test of `XWindow.set_property` in "
            "`libqtile/backend/x11/window.py`. In this single test run, `set_property` is called "
            "exactly three times, in order, with values `[]`, `12345`, and `[1, 2, 3, 5, 8]` "
            "for property name `_NET_WM_NAME`, while `xcffib.xproto.WindowError` is patched to "
            "`_DummyWindowError` and only the third `ChangePropertyChecked(...).check()` raises. "
            "Within `set_property`, internal exception handlers process multiple branches before "
            "returning. What are the exact kinds of exceptions that are caught internally during "
            "this test execution, in first-seen order?"
        ),
        "template_answer": {
            "caught_exception_kinds": ["str"]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
