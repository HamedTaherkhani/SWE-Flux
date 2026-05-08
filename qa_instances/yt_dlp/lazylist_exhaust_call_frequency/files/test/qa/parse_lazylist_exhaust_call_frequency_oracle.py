#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


# Trace plugin records every `event=call` for any frame inside
# /testbed/yt_dlp/utils/_utils.py. On Python 3.9 the recorded `funcname` is
# `yt_dlp.utils.<co_name>` (passthrough_module remaps the module to
# `yt_dlp.utils`); the line number disambiguates which class each method
# belongs to.
CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.\S+) "
    r"event=call locals=\{.*\}$",
    re.MULTILINE,
)


# (bare co_name, defining-line) pairs uniquely identify each LazyList method
# even though the trace plugin drops the class prefix on Python 3.9.
TARGETS = {
    "exhaust_call_count": ("_exhaust", 2220),
    "reverse_index_call_count": ("_reverse_index", 2230),
    "lazylist_init_call_count": ("__init__", 2205),
}


def extract_counts(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No call events found in trace.")

    pairs = Counter()
    for m in matches:
        bare = m.group("func").rsplit(".", 1)[1]
        line = int(m.group("lineno"))
        pairs[(bare, line)] += 1

    return {key: pairs.get(pair, 0) for key, pair in TARGETS.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/lazylist_exhaust_call_frequency/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/lazylist_exhaust_call_frequency/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_counts(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/lazylist_exhaust_call_frequency_test.py`, class "
            "`TestLazyListExhaustCallFrequencyQA`, method "
            "`test_lazylist_exhaust_call_frequency_case`. "
            "The test does ONE construction (`ll = LazyList(iter(range(50)))`, "
            "`LazyList.__init__` defined at line 2205 in `yt_dlp/utils/_utils.py`) and then "
            "exercises the `LazyList` (defined at line 2198) with this exact sequence: "
            "`ll[3]; ll[10:15]; ll[-5]; ll[5:]; ll[2:8:2]; ll[::-1]; len(ll)`. "
            "Inside `LazyList.__getitem__` (line 2235), the body extracts `start, stop, "
            "step` from the index, then enters the heavy branch and calls "
            "`self._exhaust()` if AND ONLY IF "
            "`((start or 0) < 0 or (stop or 0) < 0 "
            "or (start is None and step < 0) or (stop is None and step > 0))`. "
            "Otherwise it tops up `self._cache` via `itertools.islice` (no `_exhaust`). "
            "Note: for slices, `step = idx.step or 1` -- so `idx.step is None` becomes 1, "
            "while `idx.step == -1` stays -1. For int indices, `start = stop = idx` and "
            "`step = 0`, so a NEGATIVE int triggers the `(start or 0) < 0` branch but a "
            "non-negative int does NOT. `LazyList.__len__` (line 2270) calls "
            "`self._exhaust()` UNCONDITIONALLY. `LazyList._reverse_index` (a static "
            "method at line 2230) is invoked only when `self._reversed` is True (set via "
            "the `reverse=` kwarg of `__init__`); it is NOT triggered by an in-place "
            "negative-step slice like `ll[::-1]`. "
            "Report exact call counts for these three functions over the whole test "
            "method. Return a JSON object with three integer keys: "
            "`exhaust_call_count` -- number of times `LazyList._exhaust` (line 2220) is "
            "called, `reverse_index_call_count` -- number of times "
            "`LazyList._reverse_index` (line 2230) is called, and "
            "`lazylist_init_call_count` -- number of times `LazyList.__init__` (line "
            "2205) is called."
        ),
        "template_answer": {
            "exhaust_call_count": "int",
            "reverse_index_call_count": "int",
            "lazylist_init_call_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
