#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/libqtile/backend/x11/xcbq\.py:(?P<lineno>\d+) "
    r"(?P<func>libqtile\.backend\.x11\.xcbq\.(?:Colormap\.)?alloc_color) "
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
        raise ValueError("Could not find exception events for Colormap.alloc_color in trace log.")

    return {"caught_exception_kinds": seen}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "backend_x11_colormap_direct_alloc_color_caught_exception_kinds/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "backend_x11_colormap_direct_alloc_color_caught_exception_kinds/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S5_Exceptions",
        "question": (
            "Use `tests/qa/backend_x11_colormap_direct_alloc_color_caught_exception_kinds_test.py`, "
            "class `TestBackendX11ColormapDirectAllocColorCaughtExceptionKindsQA`, method "
            "`test_backend_x11_colormap_direct_alloc_color_caught_exception_kinds_case`. "
            "This is a direct backend test of `Colormap.alloc_color` in "
            "`libqtile/backend/x11/xcbq.py`. In this single test run, `alloc_color` is called "
            "exactly three times, in order: `_BadHexColor()`, `(18, 52, 86)`, and `'steelblue'`, "
            "after patching the backend's "
            "`xcffib.xproto.NameError` binding for deterministic exception injection. "
            "Within `alloc_color`, exceptions are caught in both the outer and nested "
            "`try/except` blocks. What are the exact kinds of exceptions that are caught "
            "internally during this test execution, in first-seen order?"
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
