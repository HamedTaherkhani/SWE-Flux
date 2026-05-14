#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records every line event for `unified_strdate`. Locals are
# emitted as DIFFS (only changed bindings since the previous trace event in
# the same frame). To reconstruct `upload_date` at the line-1254 event
# (`if upload_date is not None:`), walk events sequentially per call,
# accumulating the diff dict, then snapshot when reaching line 1254.
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.unified_strdate) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)

LINE_LOCALS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.unified_strdate) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_LINE = "1254"


def collect_upload_dates(trace_text: str) -> list[str]:
    locals_lookup = {
        m.start(): ast.literal_eval(m.group("locals"))
        for m in LINE_LOCALS_RE.finditer(trace_text)
    }

    cumulative: dict[str, str] = {}
    in_call = False
    captured_this_call = False
    upload_dates: list[str] = []

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
        # `event=exception` is suppressed by `contextlib.suppress(ValueError)` in
        # the format-trying loop -- the frame stays alive. Skip without exiting
        # the frame.
        if ev == "exception":
            continue
        if ev == "line" and in_call:
            delta = locals_lookup.get(m.start())
            if delta is not None:
                cumulative.update(delta)
            if ln == TARGET_LINE and not captured_this_call:
                if "upload_date" not in cumulative:
                    raise ValueError(
                        f"At line {TARGET_LINE} `upload_date` not in cumulative locals: {cumulative!r}")
                # `upload_date` is stored in the locals dict as a repr string,
                # e.g. "'20140812'". Decode the outer-quote layer.
                value = ast.literal_eval(cumulative["upload_date"])
                if value is None:
                    raise ValueError(
                        f"`upload_date` is None at line {TARGET_LINE}; test input did not parse.")
                upload_dates.append(value)
                captured_this_call = True

    if not upload_dates:
        raise ValueError("No `upload_date` observations at line 1254.")

    return upload_dates


def compute_invariants(upload_dates: list[str]) -> dict:
    lengths = {len(d) for d in upload_dates}
    length_invariant = len(lengths) == 1
    length_value = next(iter(lengths)) if length_invariant else None

    isdigits = {d.isdigit() for d in upload_dates}
    isdigit_invariant = len(isdigits) == 1
    isdigit_value = next(iter(isdigits)) if isdigit_invariant else None

    first_chars = {d[0] for d in upload_dates if d}
    first_char_invariant = len(first_chars) == 1
    first_char_value = next(iter(first_chars)) if first_char_invariant else None

    ints = [int(d) for d in upload_dates]
    mean_int_value = round(sum(ints) / len(ints), 2)

    return {
        "observation_count": len(upload_dates),
        "length_invariant": length_invariant,
        "length_value": length_value,
        "isdigit_invariant": isdigit_invariant,
        "isdigit_value": isdigit_value,
        "first_char_invariant": first_char_invariant,
        "first_char_value": first_char_value,
        "mean_int_value": mean_int_value,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/unified_strdate_upload_date_invariant_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/unified_strdate_upload_date_invariant_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    upload_dates = collect_upload_dates(trace_text)
    output = compute_invariants(upload_dates)

    qa = {
        "question_kind": "M7_Invariants",
        "question": (
            "Use the FULL test suite in "
            "`test/qa/unified_strdate_upload_date_invariant_suite_test.py` (all 18 test "
            "methods in class `TestUnifiedStrdateUploadDateInvariantSuiteQA`). Each test "
            "method calls `yt_dlp.utils._utils.unified_strdate(<date_str>)` (defined at "
            "line 1234 in `yt_dlp/utils/_utils.py`) with a different date-string literal. "
            "Inside `unified_strdate`, control eventually reaches line 1254 "
            "(`if upload_date is not None:`), at which point the local string variable "
            "`upload_date` has been bound either by line 1248 "
            "(`upload_date = dt.datetime.strptime(date_str, expression).strftime('%Y%m%d')`) "
            "inside the `for expression in date_formats(day_first):` loop, or by line 1253 "
            "(`upload_date = dt.datetime(*timetuple[:6]).strftime('%Y%m%d')`) in the "
            "`email.utils.parsedate_tz` fallback. Take ONE observation of `upload_date` "
            "PER test call, at the line-1254 trace event of that call (after the loop and "
            "fallback have settled). Across all 18 observations, determine which "
            "properties of `upload_date` are INVARIANT (i.e. take the same value across "
            "ALL 18 calls) and report the constants. Return a JSON object with EXACTLY "
            "these keys:\n"
            "- `observation_count`: int -- the number of test calls that reached line "
            "1254 with a non-None `upload_date` (all 18 inputs are valid date strings, so "
            "this should equal 18).\n"
            "- `length_invariant`: bool -- whether `len(upload_date)` is the same across "
            "all 18 observations.\n"
            "- `length_value`: int or null -- the constant value of `len(upload_date)` if "
            "`length_invariant` is true, else null.\n"
            "- `isdigit_invariant`: bool -- whether `upload_date.isdigit()` returns the "
            "same boolean across all 18 observations.\n"
            "- `isdigit_value`: bool or null -- the constant value of "
            "`upload_date.isdigit()` if `isdigit_invariant` is true, else null.\n"
            "- `first_char_invariant`: bool -- whether `upload_date[0]` is the same single "
            "character across all 18 observations.\n"
            "- `first_char_value`: str or null -- the constant value of `upload_date[0]` "
            "(a single-character string) if `first_char_invariant` is true, else null.\n"
            "- `mean_int_value`: float -- the arithmetic mean of `int(upload_date)` "
            "across all 18 observations, rounded to 2 decimal places (use Python "
            "`round(sum/n, 2)` semantics, banker's rounding)."
        ),
        "template_answer": {
            "observation_count": "int",
            "length_invariant": "bool",
            "length_value": "int_or_null",
            "isdigit_invariant": "bool",
            "isdigit_value": "bool_or_null",
            "first_char_invariant": "bool",
            "first_char_value": "str_or_null",
            "mean_int_value": "float",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
