#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records every line event for `lookup_unit_table`. The local
# `num` is bound at line 1744 (`num = float(m.group('num').replace(',', '.'))`).
# We want the value of `num` at every observed line-1745 event (the next line
# after the assignment, so `num` is already in cumulative state) -- this gives
# us one `num` value per successful call (calls that hit `if not m: return None`
# at line 1742 don't reach 1744 and contribute nothing to the range).
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.lookup_unit_table) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)

LINE_LOCALS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.lookup_unit_table) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

OBSERVE_LINE = "1745"  # `mult = unit_table[m.group('unit')]` -- by this line, `num` is already set


def extract_value_range(trace_text: str) -> dict:
    cumulative_per_call: dict[str, str] = {}
    nums: list[float] = []
    in_call = False

    # Walk events in order. Reset cumulative on `event=call`. At each
    # `event=line` whose lineno == OBSERVE_LINE, snapshot `num` from cumulative.
    # Use the diff-style `locals=` block to update cumulative.
    line_iter = LINE_LOCALS_RE.finditer(trace_text)
    line_iter_pos = 0
    line_events = []

    # Walk both regexes in lock-step is messy; simpler: walk EVENT_RE for
    # event ordering and CALL events, and pre-index LINE_LOCALS_RE matches.
    locals_lookup = {}
    for m in LINE_LOCALS_RE.finditer(trace_text):
        # use start position as a unique key
        locals_lookup[m.start()] = ast.literal_eval(m.group("locals"))

    for m in LINE_RE.finditer(trace_text):
        ev = m.group("event")
        ln = m.group("lineno")
        if ev == "call":
            cumulative_per_call = {}
            in_call = True
            continue
        if ev in {"return", "exception"}:
            in_call = False
            continue
        if ev == "line" and in_call:
            # Find matching LINE_LOCALS_RE entry at same position
            delta = locals_lookup.get(m.start())
            if delta is not None:
                cumulative_per_call.update(delta)
            if ln == OBSERVE_LINE and "num" in cumulative_per_call:
                nums.append(ast.literal_eval(cumulative_per_call["num"]))

    if not nums:
        raise ValueError("No `num` values observed at the target line.")

    return {
        "num_value_range": {
            "min": min(nums),
            "max": max(nums),
        },
        "observation_count": len(nums),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/lookup_unit_table_num_value_range_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/lookup_unit_table_num_value_range_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_value_range(trace_text)

    qa = {
        "question_kind": "M3_ProgramState",
        "question": (
            "Use the FULL test suite in "
            "`test/qa/lookup_unit_table_num_value_range_suite_test.py` (all 18 test "
            "methods in class `TestLookupUnitTableNumValueRangeSuiteQA`). Each test "
            "calls `yt_dlp.utils._utils.parse_filesize(<input>)` with a different "
            "filesize-string literal. `parse_filesize` (line 1756 in "
            "`yt_dlp/utils/_utils.py`) immediately delegates to "
            "`lookup_unit_table(unit_table, s, strict=False)` (line 1736 in the same "
            "file). Inside `lookup_unit_table`, line 1744 binds the local "
            "`num = float(m.group('num').replace(',', '.'))`. "
            "Across the FULL suite (every test contributing one observation, and only "
            "tests whose input matches the unit regex contribute -- tests with "
            "non-matching input return early at line 1742 and do not reach line 1744), "
            "what is the OBSERVED VALUE RANGE of the local `num` measured at line 1745 "
            "(the line immediately after `num` is assigned, where `num` is already "
            "fully bound)? Return JSON with the schema "
            "`{\"num_value_range\": {\"min\": <float>, \"max\": <float>}, "
            "\"observation_count\": <int>}` -- where `min` and `max` are the smallest "
            "and largest values `num` ever took across the suite, and "
            "`observation_count` is the number of distinct calls that reached line 1745. "
            "Note: the parsed string is NOT the original filesize string -- only the "
            "leading numeric prefix (which `lookup_unit_table` extracts via the named "
            "group `num` from the regex `(?P<num>...)\\s*(?P<unit>...)\\b`)."
        ),
        "template_answer": {
            "num_value_range": {"min": "float", "max": "float"},
            "observation_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
