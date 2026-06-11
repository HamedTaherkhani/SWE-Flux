#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records every line event for `mimetype2ext`. Inside, line 3002
# binds `subtype = mimetype.rpartition('/')[2]` (via tuple-unpacking
# `_, _, subtype = mimetype.rpartition('/')`). At line 3004 (`ext =
# traversal.traverse_obj(MAP, mimetype, subtype, subtype.rsplit('+')[-1])`),
# subtype is fully bound. We snapshot subtype at every line-3004 event and
# union across all tests.
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.mimetype2ext) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)

LINE_LOCALS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.mimetype2ext) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_LINE = "3004"


def extract_value_set(trace_text: str) -> dict:
    locals_lookup = {
        m.start(): ast.literal_eval(m.group("locals"))
        for m in LINE_LOCALS_RE.finditer(trace_text)
    }

    cumulative_per_call: dict[str, str] = {}
    in_call = False
    subtypes: list[str] = []

    for m in EVENT_RE.finditer(trace_text):
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
            delta = locals_lookup.get(m.start())
            if delta is not None:
                cumulative_per_call.update(delta)
            if ln == TARGET_LINE and "subtype" in cumulative_per_call:
                subtypes.append(ast.literal_eval(cumulative_per_call["subtype"]))

    if not subtypes:
        raise ValueError("No `subtype` observations at the target line.")

    distinct_sorted = sorted(set(subtypes))

    return {
        "subtype_value_set": distinct_sorted,
        "distinct_value_count": len(distinct_sorted),
        "total_observation_count": len(subtypes),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/mimetype2ext_subtype_value_set_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/mimetype2ext_subtype_value_set_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_value_set(trace_text)

    qa = {
        "question_kind": "M3_ProgramState",
        "question": (
            "Use the FULL test suite in "
            "`test/qa/mimetype2ext_subtype_value_set_suite_test.py` (all 18 test methods "
            "in class `TestMimetype2ExtSubtypeValueSetSuiteQA`). Each test method calls "
            "`yt_dlp.utils._utils.mimetype2ext(<mime>)` (defined at line 2920 in "
            "`yt_dlp/utils/_utils.py`) with a different MIME-type literal. "
            "Inside `mimetype2ext`, line 3001 normalizes the input -- "
            "`mimetype = mt.partition(';')[0].strip().lower()` -- which strips any "
            "`;`-suffixed parameters, trims whitespace, and lowercases. Then line 3002 "
            "binds the local `subtype` via "
            "`_, _, subtype = mimetype.rpartition('/')` -- i.e. the substring AFTER the "
            "LAST `/`. By line 3004 (`ext = traversal.traverse_obj(MAP, mimetype, "
            "subtype, subtype.rsplit('+')[-1])`), `subtype` is fully bound. "
            "List ALL UNIQUE values that the local `subtype` takes across the FULL test "
            "suite, measured at the line-3004 trace event of each call (one observation "
            "per test method). Return a JSON object with three keys: "
            "`subtype_value_set` -- a sorted list (ascending lexicographic order) of the "
            "distinct string values `subtype` takes across all 18 calls, "
            "`distinct_value_count` -- int, length of that list, and "
            "`total_observation_count` -- int, the total number of times `subtype` was "
            "observed at line 3004 across the suite (which equals the number of tests "
            "that reach line 3004 via the `isinstance(mt, str)` check at line 2921)."
        ),
        "template_answer": {
            "subtype_value_set": ["str"],
            "distinct_value_count": "int",
            "total_observation_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
