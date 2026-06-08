#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# Trace plugin records every `event=line` for `_separate` (mod=yt_dlp.jsinterp,
# co_name=_separate on Python 3.9). The for-loop body's first executable line
# is line 308 (`if not in_quote and char in _MATCHING_PARENS:`); each iteration
# of the for-loop at line 307 begins by emitting a line-308 event before any
# `continue` or `break`. We therefore count line-308 events.
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/jsinterp\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.jsinterp\._separate) "
    r"event=line ",
    re.MULTILINE,
)


TARGET_BODY_LINE = "308"


def extract_iteration_count(trace_text: str) -> dict:
    count = sum(
        1
        for m in LINE_RE.finditer(trace_text)
        if m.group("lineno") == TARGET_BODY_LINE
    )
    if count == 0:
        raise ValueError("No line-308 events found for _separate.")
    return {"loop_iteration_count": count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/jsinterpreter_separate_loop_iterations/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/jsinterpreter_separate_loop_iterations/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_iteration_count(trace_text)

    qa = {
        "question_kind": "S3_Loops",
        "question": (
            "Use `test/qa/jsinterpreter_separate_loop_iterations_test.py`, class "
            "`TestJsInterpreterSeparateLoopIterationsQA`, method "
            "`test_jsinterpreter_separate_loop_iterations_case`. "
            "The test calls `list(JSInterpreter._separate(EXPR, ',', max_split=2))` (the "
            "static method `_separate` of class `JSInterpreter` defined in "
            "`yt_dlp/jsinterp.py` at line 299, with the body's main for-loop at line 307: "
            "`for idx, char in enumerate(expr):`) on the exact `EXPR` literal at the top "
            "of the test file: `'(a,b),c,d,(e,f),g'`. The body of the loop maintains "
            "`counters` of nested parens, advances a delimiter-position state, and on each "
            "matched delimiter increments `splits`; the `break` at line 335 fires the "
            "moment `splits >= max_split`. Note: `_separate` is a GENERATOR -- "
            "`list(...)` drives every iteration to completion (i.e., it consumes all "
            "yields the generator emits before raising `StopIteration`). Note: a delimiter "
            "(`,`) inside a paren group does NOT trigger `splits += 1` because the "
            "`any(counters.values())` clause at line 325 short-circuits to `continue`. "
            "Report how many iterations the for-loop at line 307 EXECUTES during this test "
            "run, where one iteration is counted each time the body's first executable "
            "line (line 308) fires (every started iteration counts, including any "
            "iteration whose body ends in a `continue` or whose body terminates the loop "
            "via `break`). Return a JSON object with one integer key "
            "`loop_iteration_count`."
        ),
        "template_answer": {
            "loop_iteration_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
