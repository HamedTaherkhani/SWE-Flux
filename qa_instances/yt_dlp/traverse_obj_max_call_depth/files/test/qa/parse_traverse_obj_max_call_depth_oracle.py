#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# Trace plugin records every `event=call|return|exception` for any frame whose
# source file path starts with /testbed/yt_dlp/. We walk events in order and
# track depth as call (+1) / return (-1) / exception (-1). The peak value is
# the maximum call stack depth.
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) "
    r"event=(?P<event>call|return|exception) ",
    re.MULTILINE,
)


def extract_max_depth(trace_text: str) -> dict:
    depth = 0
    max_depth = 0

    for m in EVENT_RE.finditer(trace_text):
        event = m.group("event")
        if event == "call":
            depth += 1
            if depth > max_depth:
                max_depth = depth
        elif event in {"return", "exception"}:
            depth = max(0, depth - 1)

    if max_depth == 0:
        raise ValueError("No call events recorded for /testbed/yt_dlp/.")

    return {"maximum_call_stack_depth": max_depth}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/traverse_obj_max_call_depth/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/traverse_obj_max_call_depth/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_max_depth(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `test/qa/traverse_obj_max_call_depth_test.py`, class "
            "`TestTraverseObjMaxCallDepthQA`, method "
            "`test_traverse_obj_max_call_depth_case`. "
            "The test invokes `yt_dlp.utils.traversal.traverse_obj(DATA, PATH)` "
            "(defined at line 38 in `yt_dlp/utils/traversal.py`) with the exact `DATA` "
            "and `PATH` literals shown at the top of the test file. "
            "`traverse_obj` walks `DATA` along `PATH` using a recursive structure of "
            "nested closures (`apply_key`, `apply_path`, `_traverse_obj`, `lazy_last`) "
            "plus calls into shared helpers in other yt-dlp modules (e.g. `variadic`, "
            "`is_iterable_like`, `try_call`, the `LazyList` class for collecting "
            "branched results, `IDENTITY`, etc.). Branches in the path "
            "(`...` Ellipsis, tuple-of-paths, dict keys) cause additional recursive "
            "`apply_path` invocations. "
            "Report the MAXIMUM call stack depth reached during this test run, where "
            "depth is incremented on every Python `event=call` whose source file path "
            "begins with `/testbed/yt_dlp/` (yt-dlp's own code) and decremented on every "
            "matching `event=return` or `event=exception`. Frames in the standard "
            "library or third-party packages do NOT count. The starting depth before "
            "the very first yt-dlp call is 0; thus the first call frame has depth 1, a "
            "function it calls has depth 2, and so on. "
            "Note: under the pytest harness used here, the global trace function does "
            "NOT receive `event=call` for generator-expression frames (`<genexpr>`) "
            "even when their source file is in `/testbed/yt_dlp/`; only NAMED Python "
            "function frames (`def`-defined functions, including class methods, nested "
            "closures, lambdas, and dunder methods) emit call/return events that the "
            "trace plugin records. Count only those named-function frames. "
            "Return a JSON object with one integer key `maximum_call_stack_depth`."
        ),
        "template_answer": {
            "maximum_call_stack_depth": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
