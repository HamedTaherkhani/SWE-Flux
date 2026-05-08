#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records every line event for `parse_m3u8_attributes`. Locals
# are emitted as DIFFS (only changed bindings since the previous trace event
# in the same frame). To capture `val` at the END of every loop iteration body
# (line 4493: `info[key] = val`, the last statement of the body), walk events
# sequentially per call, accumulating the diff dict, and snapshot `val`
# whenever a line-4493 line event fires.
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.parse_m3u8_attributes) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)

LINE_LOCALS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.parse_m3u8_attributes) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_LINE = "4493"


def collect_iteration_vals(trace_text: str) -> list[str]:
    locals_lookup = {
        m.start(): ast.literal_eval(m.group("locals"))
        for m in LINE_LOCALS_RE.finditer(trace_text)
    }

    cumulative: dict[str, str] = {}
    in_call = False
    iteration_vals: list[str] = []

    for m in EVENT_RE.finditer(trace_text):
        ev = m.group("event")
        ln = m.group("lineno")
        if ev == "call":
            cumulative = {}
            in_call = True
            continue
        if ev == "return":
            in_call = False
            continue
        if ev == "exception":
            # Not expected here, but skip without exiting the frame.
            continue
        if ev == "line" and in_call:
            delta = locals_lookup.get(m.start())
            if delta is not None:
                cumulative.update(delta)
            if ln == TARGET_LINE:
                if "val" not in cumulative:
                    raise ValueError(
                        f"At line {TARGET_LINE} `val` not in cumulative locals: {cumulative!r}")
                # `val` is stored in the locals dict as a repr string,
                # e.g. "'mp4a.40.2,avc1.4d401e'". Decode the outer-quote layer.
                value = ast.literal_eval(cumulative["val"])
                iteration_vals.append(value)

    if not iteration_vals:
        raise ValueError("No iteration-end observations at line 4493.")

    return iteration_vals


def evaluate_invariant(iteration_vals: list[str]) -> dict:
    violations = [v for v in iteration_vals if "," in v]
    return {
        "total_iterations_observed": len(iteration_vals),
        "violating_iteration_count": len(violations),
        "is_invariant_always_held": len(violations) == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/parse_m3u8_attributes_loop_value_invariant_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/parse_m3u8_attributes_loop_value_invariant_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    iteration_vals = collect_iteration_vals(trace_text)
    output = evaluate_invariant(iteration_vals)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the FULL test suite in "
            "`test/qa/parse_m3u8_attributes_loop_value_invariant_suite_test.py` (all 18 "
            "test methods in class `TestParseM3u8AttributesLoopValueInvariantSuiteQA`). "
            "Each test method calls "
            "`yt_dlp.utils._utils.parse_m3u8_attributes(<attrib>)` (defined at line 4488 "
            "in `yt_dlp/utils/_utils.py`) with a different attribute-string literal. The "
            "function body is:\n"
            "```\n"
            "def parse_m3u8_attributes(attrib):\n"
            "    info = {}\n"
            "    for (key, val) in re.findall(r'(?P<key>[A-Z0-9-]+)=(?P<val>\"[^\"]+\"|[^\",]+)(?:,|$)', attrib):\n"
            "        if val.startswith('\"'):\n"
            "            val = val[1:-1]\n"
            "        info[key] = val\n"
            "    return info\n"
            "```\n"
            "Consider the LOOP INVARIANT to be checked at the END of every iteration "
            "body of the for-loop -- specifically, at the line-4493 trace event "
            "(`info[key] = val`, the last statement of the body), which fires once per "
            "iteration. The candidate invariant is:\n"
            "    INV(val) := ',' not in val\n"
            "i.e., the local string variable `val` (after the optional "
            "`val = val[1:-1]` strip on line 4492) does NOT contain a comma character. "
            "Report whether this invariant is held in EVERY iteration across ALL 18 test "
            "calls. Note: an iteration counts even if the test only triggers a single "
            "iteration; total iterations observed = sum of for-loop iterations across all "
            "tests. Return a JSON object with EXACTLY these three keys:\n"
            "- `total_iterations_observed`: int -- total number of for-loop iterations "
            "completed across all 18 test calls (i.e., total line-4493 trace events).\n"
            "- `violating_iteration_count`: int -- number of iterations in which "
            "INV(val) is FALSE (i.e., `,' in val`).\n"
            "- `is_invariant_always_held`: bool -- True iff "
            "`violating_iteration_count == 0`."
        ),
        "template_answer": {
            "total_iterations_observed": "int",
            "violating_iteration_count": "int",
            "is_invariant_always_held": "bool",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
