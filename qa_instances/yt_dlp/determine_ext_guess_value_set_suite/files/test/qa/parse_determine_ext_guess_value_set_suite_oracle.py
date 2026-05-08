#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records every line event for `determine_ext`. Locals are
# emitted as DIFFS. The function body is:
#     1292: def determine_ext(url, default_ext='unknown_video'):
#     1293:     if url is None or '.' not in url:
#     1294:         return default_ext
#     1295:     guess = url.partition('?')[0].rpartition('.')[2]
#     1296:     if re.match(r'^[A-Za-z0-9]+$', guess):
#     1297:         return guess
#     1298:     elif guess.rstrip('/') in KNOWN_EXTENSIONS:
#     1299:         return guess.rstrip('/')
#     1300:     else:
#     1301:         return default_ext
# At the line-1296 trace event, line-1295's assignment to `guess` has just
# executed, so the cumulative locals include `guess`. We snapshot at that
# event for every call (skip calls that returned early at line 1294 because
# the URL had no '.').
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.determine_ext) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)

LINE_LOCALS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.determine_ext) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_LINE = "1296"


def collect_guess_values(trace_text: str) -> list[str]:
    locals_lookup = {
        m.start(): ast.literal_eval(m.group("locals"))
        for m in LINE_LOCALS_RE.finditer(trace_text)
    }

    cumulative: dict[str, str] = {}
    in_call = False
    captured_this_call = False
    values: list[str] = []

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
                if "guess" not in cumulative:
                    raise ValueError(
                        f"At line {TARGET_LINE} `guess` not in cumulative "
                        f"locals: {cumulative!r}")
                value = ast.literal_eval(cumulative["guess"])
                values.append(value)
                captured_this_call = True

    if not values:
        raise ValueError("No `guess` observations at line 1296.")

    return values


def evaluate(values: list[str]) -> dict:
    distinct_sorted = sorted(set(values))
    return {
        "guess_value_set": distinct_sorted,
        "distinct_value_count": len(distinct_sorted),
        "total_observation_count": len(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/determine_ext_guess_value_set_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/determine_ext_guess_value_set_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    values = collect_guess_values(trace_text)
    output = evaluate(values)

    qa = {
        "question_kind": "value_range_analysis",
        "question": (
            "Use the FULL test suite in "
            "`test/qa/determine_ext_guess_value_set_suite_test.py` (all 18 test methods "
            "in class `TestDetermineExtGuessValueSetSuiteQA`). Each test method calls "
            "`yt_dlp.utils._utils.determine_ext(<url>)` (defined at line 1292 in "
            "`yt_dlp/utils/_utils.py`) with a different URL string. The function body "
            "is:\n"
            "```\n"
            "1292: def determine_ext(url, default_ext='unknown_video'):\n"
            "1293:     if url is None or '.' not in url:\n"
            "1294:         return default_ext\n"
            "1295:     guess = url.partition('?')[0].rpartition('.')[2]\n"
            "1296:     if re.match(r'^[A-Za-z0-9]+$', guess):\n"
            "1297:         return guess\n"
            "1298:     # Try extract ext from URLs like http://example.com/foo/bar.mp4/?download\n"
            "1299:     elif guess.rstrip('/') in KNOWN_EXTENSIONS:\n"
            "1300:         return guess.rstrip('/')\n"
            "1301:     else:\n"
            "1302:         return default_ext\n"
            "```\n\n"
            "For EACH test call that REACHES line 1296 (i.e., did NOT take the "
            "early-return at line 1294 because the URL had no `.`), snapshot the local "
            "string variable `guess` at the line-1296 trace event (i.e., AFTER line "
            "1295's assignment but BEFORE line 1296's `re.match` is evaluated). All 18 "
            "URLs in this suite contain at least one `.` character, so every call "
            "produces exactly one observation of `guess`.\n\n"
            "IMPORTANT: report the value of the LOCAL `guess` itself, NOT the function's "
            "return value. In particular, for a URL such as "
            "`https://example.com/foo/bar.ogg/` the rpartition by `.` on "
            "`'https://example.com/foo/bar.ogg/'` yields the suffix `'ogg/'` "
            "(WITH the trailing slash). The function's RETURN value would strip the "
            "slash via `guess.rstrip('/')` at line 1300, but the LOCAL `guess` at line "
            "1296 still contains the raw suffix `'ogg/'`. List ALL UNIQUE values that "
            "the local `guess` takes across the 18 test calls.\n\n"
            "Return a JSON object with EXACTLY these three keys:\n"
            "- `guess_value_set`: list of str -- the SORTED list (ascending lexicographic "
            "order, Python default `sorted()`) of distinct string values that `guess` "
            "takes across the 18 calls.\n"
            "- `distinct_value_count`: int -- length of `guess_value_set`.\n"
            "- `total_observation_count`: int -- the total number of times `guess` was "
            "observed at line 1296 across the suite (equals the number of tests that "
            "reach line 1296; should be 18 since every test URL contains a `.`)."
        ),
        "template_answer": {
            "guess_value_set": ["str"],
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
