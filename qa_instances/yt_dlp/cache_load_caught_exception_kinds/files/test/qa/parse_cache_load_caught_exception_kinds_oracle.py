#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# Trace plugin records the function as `yt_dlp.cache.load` on Python 3.9
# (mod=yt_dlp.cache, co_name=load -- there is no `co_qualname` until 3.11,
# so the class prefix is dropped). The file `cache.py` contains only one
# `load` method (`Cache.load`), so this is unambiguous.
EXCEPTION_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/cache\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.cache\.load) "
    r"event=exception exc=(?P<exc_type>[^:]+): ",
    re.MULTILINE,
)


def extract_exception_kinds(trace_text: str) -> dict:
    matches = list(EXCEPTION_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No exception event for Cache.load in trace.")
    seen_in_order: list[str] = []
    for m in matches:
        exc_type = m.group("exc_type").strip()
        if exc_type not in seen_in_order:
            seen_in_order.append(exc_type)
    all_events = [m.group("exc_type").strip() for m in matches]
    return {
        "caught_exception_kinds_first_seen_order": seen_in_order,
        "caught_exception_event_count": len(all_events),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/cache_load_caught_exception_kinds/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/cache_load_caught_exception_kinds/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_exception_kinds(trace_text)

    qa = {
        "question_kind": "abnormal_behavior_prediction",
        "question": (
            "Use `test/qa/cache_load_caught_exception_kinds_test.py`, class "
            "`TestCacheLoadCaughtExceptionKindsQA`, method "
            "`test_cache_load_caught_exception_kinds_case`. "
            "The test instantiates `yt_dlp.cache.Cache` with a stub `_StubYDL` (whose "
            "`params` only sets `cachedir`) and invokes `cache.load(SECTION, key)` (defined "
            "at line 56 in `yt_dlp/cache.py`) THREE times in sequence -- once per "
            "scenario A/B/C in the test body. `Cache.load`'s body wraps its file-read "
            "logic inside `with contextlib.suppress(OSError):` (line 64) and additionally "
            "inside an inner `try: ... except (ValueError, KeyError):` (lines 65-72) that "
            "in turn contains another `try: os.path.getsize(cache_fn) except OSError as oe:` "
            "(lines 67-69). Note: the actual classes raised by Python "
            "(`json.JSONDecodeError`, `FileNotFoundError`, etc.) are subclasses of the "
            "broader exception types written in the `except` clauses; the trace records the "
            "*concrete* class name actually raised, not the class declared in `except`. "
            "Report the exact set of exception kinds that propagate through the "
            "`Cache.load` frame and are caught somewhere along this run. "
            "Return a JSON object with two keys: "
            "`caught_exception_kinds_first_seen_order` (list[str], the bare class names of "
            "the caught exceptions in first-seen order across the three calls), and "
            "`caught_exception_event_count` (int, the total number of exception events the "
            "`Cache.load` frame observes during this test, counting repeats)."
        ),
        "template_answer": {
            "caught_exception_kinds_first_seen_order": ["str"],
            "caught_exception_event_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
