#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import json
import re
from pathlib import Path


RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.extract_timezone) "
    r"event=return retval=(?P<retval>.*?) locals=\{.*\}$",
    re.MULTILINE,
)


def extract_return_tuple(trace_text: str) -> tuple:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No extract_timezone return event in trace log.")
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly 1 extract_timezone return event, got {len(matches)}.")

    retval_text = matches[0].group("retval")
    safe_globals = {"datetime": datetime, "__builtins__": {}}
    value = eval(retval_text, safe_globals, {})  # noqa: S307

    if not (isinstance(value, tuple) and len(value) == 2):
        raise ValueError(f"Unexpected return shape: {value!r}")
    tz, remaining = value
    if not isinstance(tz, datetime.timedelta):
        raise ValueError(f"First element is not a timedelta: {tz!r}")
    if not isinstance(remaining, str):
        raise ValueError(f"Second element is not a str: {remaining!r}")
    return tz, remaining


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/unified_timestamp_helper_indirect_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/unified_timestamp_helper_indirect_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    tz, remaining = extract_return_tuple(trace_text)

    oracle_answer = {
        "timezone_total_seconds": int(tz.total_seconds()),
        "remaining_date_str": remaining,
    }

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `test/qa/unified_timestamp_helper_indirect_output_test.py`, class "
            "`TestUnifiedTimestampHelperIndirectOutputQA`, method "
            "`test_unified_timestamp_helper_indirect_output_case`. "
            "The test calls `yt_dlp.utils._utils.unified_timestamp(date_str)` (defined in "
            "`yt_dlp/utils/_utils.py` at line 1258) with `date_str = "
            "'Wednesday|2024-08-14T06:30:45.987-04:30'`. "
            "During this single call, `unified_timestamp` invokes the helper "
            "`yt_dlp.utils._utils.extract_timezone` (defined at line 1179 in the same file) "
            "exactly once. Note that `unified_timestamp` performs preprocessing (day-of-week / "
            "comma / pipe stripping and whitespace collapsing) on the input before calling "
            "`extract_timezone`, so the argument seen by `extract_timezone` is not identical "
            "to the test input. "
            "Report the exact return value of that single `extract_timezone` invocation as a "
            "JSON object with two keys: `timezone_total_seconds` (int, the value of the "
            "returned `datetime.timedelta`'s `.total_seconds()` cast to int) and "
            "`remaining_date_str` (str, the second element of the returned tuple, byte-for-byte)."
        ),
        "template_answer": {
            "timezone_total_seconds": "int",
            "remaining_date_str": "str",
        },
        "oracle_answer": oracle_answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
