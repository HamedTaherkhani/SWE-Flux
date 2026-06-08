#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# Trace plugin records every line/call/return event for `format_to_regex`. We
# split the trace into per-call line-number sequences (each `event=call`
# starts a new sequence; `event=line` events extend it; `event=return` /
# `event=exception` close it). We then check whether all 5 per-call sequences
# are identical.
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/postprocessor/metadataparser\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.postprocessor\.metadataparser\.format_to_regex) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)


def extract_path_determinism(trace_text: str) -> dict:
    sequences: list[list[int]] = []
    current: list[int] | None = None

    for m in EVENT_RE.finditer(trace_text):
        ev = m.group("event")
        ln = int(m.group("lineno"))
        if ev == "call":
            current = []
            sequences.append(current)
        elif ev == "line" and current is not None:
            current.append(ln)
        elif ev in {"return", "exception"} and current is not None:
            current = None

    if len(sequences) != 5:
        raise ValueError(
            f"Expected exactly 5 format_to_regex calls, got {len(sequences)}.")

    first = sequences[0]
    all_same = all(seq == first for seq in sequences)
    distinct_count = len({tuple(seq) for seq in sequences})

    return {
        "all_paths_identical": all_same,
        "distinct_path_count": distinct_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/format_to_regex_path_determinism/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/format_to_regex_path_determinism/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_path_determinism(trace_text)

    qa = {
        "question_kind": "S1_IntraProceduralCFG",
        "question": (
            "Use `test/qa/format_to_regex_path_determinism_test.py`, class "
            "`TestFormatToRegexPathDeterminismQA`, method "
            "`test_format_to_regex_path_determinism_case`. "
            "The test runs the following block exactly once:\n"
            "```\n"
            "results = []\n"
            "for _ in range(5):\n"
            "    results.append(MetadataParserPP.format_to_regex(FMT))\n"
            "```\n"
            "where `FMT = '%(title)s - %(artist)s [%(album)s].%(ext)s'` is the literal "
            "shown at the top of the test file, and `format_to_regex` is the static method "
            "of class `MetadataParserPP` defined at line 38 in "
            "`yt_dlp/postprocessor/metadataparser.py`. The method body uses only stdlib "
            "regex helpers (`re.search`, `re.finditer`, `re.escape`) and a single string "
            "accumulator `regex` plus a position cursor `lastpos`; it does NOT use the "
            "`random` module, `time`, `id()`, sets, or any other source whose output "
            "varies across invocations within a single Python process. "
            "Across the 5 sequential calls to `format_to_regex(FMT)` performed by this "
            "test (one per loop iteration, in iteration order), do all 5 calls execute "
            "the EXACT same sequence of line numbers inside `format_to_regex`? "
            "Return a JSON object with two keys: `all_paths_identical` -- boolean, `true` "
            "if all 5 per-call line-number sequences match the first one element-by-"
            "element, `false` otherwise -- and `distinct_path_count` -- int, the number "
            "of distinct line-number sequences across the five calls (1 means every call "
            "took the same path; 5 means every call took a different path)."
        ),
        "template_answer": {
            "all_paths_identical": "bool",
            "distinct_path_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
