#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


# Trace plugin records every line event for `parse_age_limit`. We DON'T need
# locals here -- only the set of line numbers that fire `event=line` per call
# frame. We bracket each call by `event=call` ... `event=return` and collect
# the set of lines hit in between.
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.parse_age_limit) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)


def collect_per_call_lines(trace_text: str) -> list[set[int]]:
    per_call: list[set[int]] = []
    current: set[int] = set()
    in_call = False

    for m in EVENT_RE.finditer(trace_text):
        ev = m.group("event")
        ln = int(m.group("lineno"))
        if ev == "call":
            current = set()
            in_call = True
            continue
        if ev == "return":
            per_call.append(current)
            in_call = False
            continue
        if ev == "exception":
            # Not expected; skip without exiting frame.
            continue
        if ev == "line" and in_call:
            current.add(ln)

    if not per_call:
        raise ValueError("No completed `parse_age_limit` calls captured.")

    return per_call


def evaluate(per_call_lines: list[set[int]]) -> dict:
    union_lines: set[int] = set()
    for s in per_call_lines:
        union_lines |= s

    if per_call_lines:
        intersection_lines = set(per_call_lines[0])
        for s in per_call_lines[1:]:
            intersection_lines &= s
    else:
        intersection_lines = set()

    line_to_count: dict[int, int] = defaultdict(int)
    for s in per_call_lines:
        for ln in s:
            line_to_count[ln] += 1
    lines_covered_by_only_one_test = sorted(
        ln for ln, c in line_to_count.items() if c == 1)

    return {
        "total_calls_observed": len(per_call_lines),
        "total_unique_lines_covered_by_at_least_one_test": len(union_lines),
        "union_lines_sorted": sorted(union_lines),
        "total_lines_covered_by_every_test": len(intersection_lines),
        "intersection_lines_sorted": sorted(intersection_lines),
        "lines_covered_by_only_one_test": lines_covered_by_only_one_test,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/parse_age_limit_line_coverage_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/parse_age_limit_line_coverage_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    per_call_lines = collect_per_call_lines(trace_text)
    output = evaluate(per_call_lines)

    qa = {
        "question_kind": "M1_IntraProceduralCFG",
        "question": (
            "Use the FULL test suite in "
            "`test/qa/parse_age_limit_line_coverage_suite_test.py` (all 18 test methods "
            "in class `TestParseAgeLimitLineCoverageSuiteQA`). Each test method calls "
            "`yt_dlp.utils._utils.parse_age_limit(<arg>)` (defined at line 2719 in "
            "`yt_dlp/utils/_utils.py`) with a different argument. The function body is:\n"
            "```\n"
            "2719: def parse_age_limit(s):\n"
            "2720:     # isinstance(False, int) is True. So type() must be used instead\n"
            "2721:     if type(s) is int:  # noqa: E721\n"
            "2722:         return s if 0 <= s <= 21 else None\n"
            "2723:     elif not isinstance(s, str):\n"
            "2724:         return None\n"
            "2725:     m = re.match(r'^(?P<age>\\d{1,2})\\+?$', s)\n"
            "2726:     if m:\n"
            "2727:         return int(m.group('age'))\n"
            "2728:     s = s.upper()\n"
            "2729:     if s in US_RATINGS:\n"
            "2730:         return US_RATINGS[s]\n"
            "2731:     m = re.match(r'^TV[_-]?({})$'.format('|'.join(k[3:] for k in TV_PARENTAL_GUIDELINES)), s)\n"
            "2732:     if m:\n"
            "2733:         return TV_PARENTAL_GUIDELINES['TV-' + m.group(1)]\n"
            "2734:     return None\n"
            "```\n"
            "Where `US_RATINGS = {'G': 0, 'PG': 10, 'PG-13': 13, 'R': 16, 'NC': 18}` and "
            "`TV_PARENTAL_GUIDELINES = {'TV-Y': 0, 'TV-Y7': 7, 'TV-G': 0, 'TV-PG': 0, "
            "'TV-14': 14, 'TV-MA': 17}` (i.e., the keys of `US_RATINGS` are 'G','PG',"
            "'PG-13','R','NC' and the second alternative in the TV regex matches strings "
            "of the form `TV[_-]?<KEY>` where `<KEY>` is the suffix after `TV-` of any "
            "key in `TV_PARENTAL_GUIDELINES`).\n\n"
            "For EACH test, determine the SET of LINE NUMBERS in `parse_age_limit` (lines "
            "2719-2734) at which the Python tracer fires an `event=line` (i.e., the "
            "executable lines visited during that call). Lines 2719 (the `def`) and 2720 "
            "(the comment) do NOT receive `event=line` events -- only lines 2721 through "
            "2734 are candidates. Aggregate across the 18 test calls and return a JSON "
            "object with EXACTLY these six keys:\n"
            "- `total_calls_observed`: int -- total number of completed call frames "
            "(should equal 18).\n"
            "- `total_unique_lines_covered_by_at_least_one_test`: int -- size of the "
            "UNION of per-test line sets.\n"
            "- `union_lines_sorted`: list of int -- the union of per-test line sets, "
            "sorted ascending.\n"
            "- `total_lines_covered_by_every_test`: int -- size of the INTERSECTION of "
            "per-test line sets (lines hit in EVERY one of the 18 calls).\n"
            "- `intersection_lines_sorted`: list of int -- the intersection of per-test "
            "line sets, sorted ascending.\n"
            "- `lines_covered_by_only_one_test`: list of int -- line numbers that are hit "
            "by EXACTLY ONE of the 18 calls (count == 1), sorted ascending."
        ),
        "template_answer": {
            "total_calls_observed": "int",
            "total_unique_lines_covered_by_at_least_one_test": "int",
            "union_lines_sorted": ["int"],
            "total_lines_covered_by_every_test": "int",
            "intersection_lines_sorted": ["int"],
            "lines_covered_by_only_one_test": ["int"],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
