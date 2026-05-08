#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records every line event for `js_number_to_string`. Locals are
# emitted as DIFFS (only changed bindings since the previous trace event in
# the same frame). We focus on Loop 2 (lines 143-145, integer-part loop):
#     while integer > 0:                              # line 143
#         integer, digit = divmod(integer, radix)    # line 144
#         result.appendleft(digit)                    # line 145
# At every line-145 trace event (i.e., once per loop iteration), `integer`
# and `digit` have been updated by line 144's divmod. We accumulate diff-style
# locals per call and snapshot (integer, digit) at every line-145 event.
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/jsinterp\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.jsinterp\.js_number_to_string) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)

LINE_LOCALS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/jsinterp\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.jsinterp\.js_number_to_string) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_LINE = "145"


def collect_per_call_digit_sequences(trace_text: str) -> list[list[int]]:
    locals_lookup = {
        m.start(): ast.literal_eval(m.group("locals"))
        for m in LINE_LOCALS_RE.finditer(trace_text)
    }

    cumulative: dict[str, str] = {}
    in_call = False
    current_call_digits: list[int] = []
    per_call_digits: list[list[int]] = []

    for m in EVENT_RE.finditer(trace_text):
        ev = m.group("event")
        ln = m.group("lineno")
        if ev == "call":
            cumulative = {}
            current_call_digits = []
            in_call = True
            continue
        if ev == "return":
            per_call_digits.append(current_call_digits)
            in_call = False
            continue
        if ev == "exception":
            # Not expected in this function, but skip without exiting.
            continue
        if ev == "line" and in_call:
            delta = locals_lookup.get(m.start())
            if delta is not None:
                cumulative.update(delta)
            if ln == TARGET_LINE:
                if "digit" not in cumulative:
                    raise ValueError(
                        f"At line {TARGET_LINE} `digit` not in cumulative locals: {cumulative!r}")
                digit_value = ast.literal_eval(cumulative["digit"])
                current_call_digits.append(int(digit_value))

    if not per_call_digits:
        raise ValueError("No completed calls captured.")

    return per_call_digits


def classify_sequence(seq: list[int]) -> str:
    if len(seq) < 2:
        return "other"
    strictly_increasing = all(seq[i + 1] > seq[i] for i in range(len(seq) - 1))
    strictly_decreasing = all(seq[i + 1] < seq[i] for i in range(len(seq) - 1))
    if strictly_increasing:
        return "strict_inc"
    if strictly_decreasing:
        return "strict_dec"
    return "other"


def evaluate(per_call_digits: list[list[int]]) -> dict:
    classes = [classify_sequence(seq) for seq in per_call_digits]
    count_inc = classes.count("strict_inc")
    count_dec = classes.count("strict_dec")
    count_other = classes.count("other")
    return {
        "total_calls_observed": len(per_call_digits),
        "count_strictly_increasing": count_inc,
        "count_strictly_decreasing": count_dec,
        "count_other": count_other,
        "is_digit_strictly_monotonic_in_every_call": count_other == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/js_number_to_string_loop_var_monotonic_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/js_number_to_string_loop_var_monotonic_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    per_call_digits = collect_per_call_digit_sequences(trace_text)
    output = evaluate(per_call_digits)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the FULL test suite in "
            "`test/qa/js_number_to_string_loop_var_monotonic_suite_test.py` (all 18 test "
            "methods in class `TestJsNumberToStringLoopVarMonotonicSuiteQA`). Each test "
            "method calls `yt_dlp.jsinterp.js_number_to_string(<val>, <radix>)` (defined "
            "at line 99 in `yt_dlp/jsinterp.py`) with a positive INTEGER `val` and a "
            "`radix` in [2, 36]. The function contains an integer-part loop at lines "
            "143-145:\n"
            "```\n"
            "    integer, digit = divmod(int(integer), radix)   # line 141 (BEFORE the loop)\n"
            "    result.appendleft(digit)                        # line 142\n"
            "    while integer > 0:                              # line 143\n"
            "        integer, digit = divmod(integer, radix)    # line 144\n"
            "        result.appendleft(digit)                    # line 145\n"
            "```\n"
            "For EVERY trace event at LINE 145 of EVERY call (i.e., once per iteration of "
            "the while loop on line 143), record the local `digit`. Concatenate per-call "
            "into a sequence in iteration order. Note: the line-141 `digit` (before the "
            "loop) is NOT included in the sequence -- only line-145 events are counted. A "
            "call where `int(abs(val)) < radix` (i.e., the original integer part has only "
            "one base-`radix` digit) will produce an EMPTY sequence because the while "
            "loop never executes.\n\n"
            "MONOTONICITY QUESTION: For each test call, classify its `digit` sequence as:\n"
            "- `strict_inc` if the sequence has length >= 2 AND every consecutive pair "
            "is STRICTLY increasing (no equal consecutive values, no decreases).\n"
            "- `strict_dec` if the sequence has length >= 2 AND every consecutive pair "
            "is STRICTLY decreasing.\n"
            "- `other` otherwise. This includes: length < 2 (empty or singleton), "
            "constant sequences, sequences with any plateau (equal consecutive pair), or "
            "sequences with any direction change.\n\n"
            "Return a JSON object with EXACTLY these five keys:\n"
            "- `total_calls_observed`: int -- total number of `js_number_to_string` "
            "frames captured (should equal 18).\n"
            "- `count_strictly_increasing`: int -- number of test calls classified as "
            "`strict_inc`.\n"
            "- `count_strictly_decreasing`: int -- number of test calls classified as "
            "`strict_dec`.\n"
            "- `count_other`: int -- number of test calls classified as `other`.\n"
            "- `is_digit_strictly_monotonic_in_every_call`: bool -- True iff "
            "`count_other == 0`."
        ),
        "template_answer": {
            "total_calls_observed": "int",
            "count_strictly_increasing": "int",
            "count_strictly_decreasing": "int",
            "count_other": "int",
            "is_digit_strictly_monotonic_in_every_call": "bool",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
