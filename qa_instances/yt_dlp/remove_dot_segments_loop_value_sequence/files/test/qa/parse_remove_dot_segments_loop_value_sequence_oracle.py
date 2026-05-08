#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin emits one `event=line` per executed line in `remove_dot_segments`
# whose `locals=...` block contains only the locals that *changed* since the
# previous event. Walk events in order, maintain a cumulative snapshot, and
# read the current `s` value at every line-252 event (the first body line of
# the for-loop, which fires once per iteration with `s` already bound to the
# iteration's segment value).
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/networking\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.networking\.remove_dot_segments) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


# Line 252: `if s == '.':` -- the first line of the for-loop body. Fires once
# per iteration, with `s` already bound to the iteration's segment.
TARGET_LINE = "252"


def extract_value_sequence(trace_text: str) -> dict:
    cumulative: dict[str, str] = {}
    s_sequence: list[str] = []

    for m in LINE_RE.finditer(trace_text):
        delta = ast.literal_eval(m.group("locals"))
        cumulative.update(delta)
        if m.group("lineno") == TARGET_LINE:
            if "s" not in cumulative:
                raise ValueError(
                    f"`s` not in cumulative state at line {TARGET_LINE} event")
            s_sequence.append(ast.literal_eval(cumulative["s"]))

    if not s_sequence:
        raise ValueError(f"No line-{TARGET_LINE} events found.")

    return {
        "s_value_sequence": s_sequence,
        "iteration_count": len(s_sequence),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/remove_dot_segments_loop_value_sequence/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/remove_dot_segments_loop_value_sequence/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_value_sequence(trace_text)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `test/qa/remove_dot_segments_loop_value_sequence_test.py`, class "
            "`TestRemoveDotSegmentsLoopValueSequenceQA`, method "
            "`test_remove_dot_segments_loop_value_sequence_case`. "
            "The test calls `yt_dlp.utils.networking.remove_dot_segments(PATH)` (defined "
            "at line 245 in `yt_dlp/utils/networking.py`) with the exact `PATH` literal "
            "at the top of the test file: `'/a//b/./c/.././../f/'`. "
            "Inside `remove_dot_segments`, line 250 splits `path` on `/` to produce "
            "`segments`, then line 251 begins `for s in segments:` whose body starts at "
            "line 252 (`if s == '.':`). On each iteration the loop variable `s` is "
            "REASSIGNED to the next element of `segments` (Python's standard `str.split` "
            "preserves empty strings for adjacent separators and for leading/trailing "
            "slashes). "
            "Report the ORDERED list of every value bound to the loop variable `s` during "
            "this run, with each iteration contributing exactly one entry to the list, in "
            "iteration order. Duplicates and consecutive-duplicate values both count -- "
            "two iterations that bind `s` to the same string produce two consecutive "
            "entries in the output list. The body of the loop never reassigns `s` (only "
            "`output` is mutated), so each list entry is exactly the segment value Python "
            "bound when entering that iteration. "
            "Return a JSON object with two keys: `s_value_sequence` (a list of strings, "
            "one per iteration in order) and `iteration_count` (int, the length of that "
            "list)."
        ),
        "template_answer": {
            "s_value_sequence": ["str"],
            "iteration_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
