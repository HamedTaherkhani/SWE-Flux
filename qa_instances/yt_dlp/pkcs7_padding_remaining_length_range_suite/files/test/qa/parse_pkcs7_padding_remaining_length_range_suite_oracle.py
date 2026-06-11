#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records every line event for `pkcs7_padding`. Locals are
# emitted as DIFFS. The function body is small:
#     line 45: remaining_length = BLOCK_SIZE_BYTES - len(data) % BLOCK_SIZE_BYTES
#     line 46: return data + [remaining_length] * remaining_length
# At line-46's event, line-45 has just executed, so the cumulative locals
# include `remaining_length`. We snapshot at the line-46 event of every call.
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/aes\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.aes\.pkcs7_padding) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)

LINE_LOCALS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/aes\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.aes\.pkcs7_padding) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_LINE = "46"


def collect_remaining_lengths(trace_text: str) -> list[int]:
    locals_lookup = {
        m.start(): ast.literal_eval(m.group("locals"))
        for m in LINE_LOCALS_RE.finditer(trace_text)
    }

    cumulative: dict[str, str] = {}
    in_call = False
    captured_this_call = False
    values: list[int] = []

    for m in EVENT_RE.finditer(trace_text):
        ev = m.group("event")
        ln = m.group("lineno")
        if ev == "call":
            cumulative = {}
            in_call = True
            captured_this_call = False
            continue
        if ev == "return":
            in_call = False
            continue
        if ev == "exception":
            continue
        if ev == "line" and in_call:
            delta = locals_lookup.get(m.start())
            if delta is not None:
                cumulative.update(delta)
            if ln == TARGET_LINE and not captured_this_call:
                if "remaining_length" not in cumulative:
                    raise ValueError(
                        f"At line {TARGET_LINE} `remaining_length` not in cumulative "
                        f"locals: {cumulative!r}")
                value = ast.literal_eval(cumulative["remaining_length"])
                values.append(int(value))
                captured_this_call = True

    if not values:
        raise ValueError("No `remaining_length` observations at line 46.")

    return values


def evaluate(values: list[int]) -> dict:
    distinct = sorted(set(values))
    return {
        "total_calls_observed": len(values),
        "min_value": min(values),
        "max_value": max(values),
        "range": max(values) - min(values),
        "distinct_values_count": len(distinct),
        "mean_value": round(sum(values) / len(values), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/pkcs7_padding_remaining_length_range_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/pkcs7_padding_remaining_length_range_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    values = collect_remaining_lengths(trace_text)
    output = evaluate(values)

    qa = {
        "question_kind": "M3_ProgramState",
        "question": (
            "Use the FULL test suite in "
            "`test/qa/pkcs7_padding_remaining_length_range_suite_test.py` (all 18 test "
            "methods in class `TestPkcs7PaddingRemainingLengthRangeSuiteQA`). Each test "
            "method calls `yt_dlp.aes.pkcs7_padding(<data>)` (defined at line 37 in "
            "`yt_dlp/aes.py`) with a list of integers as `data`. The function body is:\n"
            "```\n"
            "30: BLOCK_SIZE_BYTES = 16\n"
            "...\n"
            "37: def pkcs7_padding(data):\n"
            "38:     \"\"\"\n"
            "39:     PKCS#7 padding\n"
            "40: \n"
            "41:     @param {int[]} data        cleartext\n"
            "42:     @returns {int[]}           padding data\n"
            "43:     \"\"\"\n"
            "44: \n"
            "45:     remaining_length = BLOCK_SIZE_BYTES - len(data) % BLOCK_SIZE_BYTES\n"
            "46:     return data + [remaining_length] * remaining_length\n"
            "```\n\n"
            "For EACH test call, snapshot the local integer variable `remaining_length` "
            "at the line-46 trace event (i.e., AFTER line 45 has executed and assigned "
            "`remaining_length`, but BEFORE line 46's return expression has been "
            "evaluated). Take ONE observation of `remaining_length` per test call (18 "
            "observations total). Across the 18 observed values, determine the value "
            "range and aggregate statistics. Return a JSON object with EXACTLY these six "
            "keys:\n"
            "- `total_calls_observed`: int -- total number of `pkcs7_padding` frames "
            "captured (should equal 18).\n"
            "- `min_value`: int -- the MINIMUM observed value of `remaining_length` "
            "across the 18 calls.\n"
            "- `max_value`: int -- the MAXIMUM observed value.\n"
            "- `range`: int -- `max_value - min_value`.\n"
            "- `distinct_values_count`: int -- the number of DISTINCT integer values "
            "that `remaining_length` takes across the 18 calls (size of the set).\n"
            "- `mean_value`: float -- the arithmetic mean of `remaining_length` across "
            "the 18 calls, rounded to 2 decimal places (use Python `round(sum/n, 2)` "
            "semantics, banker's rounding)."
        ),
        "template_answer": {
            "total_calls_observed": "int",
            "min_value": "int",
            "max_value": "int",
            "range": "int",
            "distinct_values_count": "int",
            "mean_value": "float",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
