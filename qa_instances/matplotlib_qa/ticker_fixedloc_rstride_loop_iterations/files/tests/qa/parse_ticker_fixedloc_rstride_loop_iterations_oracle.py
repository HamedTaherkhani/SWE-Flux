#!/usr/bin/env python3
"""
Count iterations of `for i in range(1, step):` in FixedLocator.tick_values
(loop body starts at line 1804 in lib/matplotlib/ticker.py, header line 1803).

Fingerprints FixedLocator via line 1801 (unique ceil(len/nbins) assignment).
Clears on return at line 1807 (`return self.raise_if_exceeds(ticks)`).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/lib/matplotlib/ticker.py"
FP_LINE_FIXED_TICK_VALUES = 1801
LOOP_BODY_LINE = 1804
RETURN_LINE = 1807

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} (?P<path>/testbed[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _is_tick_values_func(func: str) -> bool:
    return func.endswith(".tick_values")


def count_rstride_loop_iterations(trace_text: str) -> int:
    tv_depth = 0
    fixed_active = False
    count = 0

    for raw in trace_text.splitlines():
        m = EVENT_RE.match(raw)
        if not m:
            continue

        path = m.group("path")
        lineno = int(m.group("lineno"))
        func = m.group("func")
        event = m.group("event")

        if path != TARGET_PATH:
            continue

        if event == "call" and _is_tick_values_func(func):
            tv_depth += 1
            fixed_active = False
            continue

        if event in ("return", "exception") and _is_tick_values_func(func):
            if fixed_active and tv_depth >= 1 and lineno == RETURN_LINE:
                fixed_active = False
            if tv_depth >= 1:
                tv_depth -= 1
            continue

        if event != "line":
            continue

        if not _is_tick_values_func(func):
            continue

        if tv_depth < 1:
            continue

        if lineno == FP_LINE_FIXED_TICK_VALUES:
            fixed_active = True
            continue

        if fixed_active and lineno == LOOP_BODY_LINE:
            count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/ticker_fixedloc_rstride_loop_iterations/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/ticker_fixedloc_rstride_loop_iterations/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    iteration_count = count_rstride_loop_iterations(trace_text)

    question = (
        "Use `tests/qa/ticker_fixedloc_rstride_loop_iterations_test.py`, class "
        "`TestTickerFixedlocRstrideLoopIterationsQA`, method "
        "`test_ticker_fixedloc_rstride_loop_iterations_case`. "
        "The test builds a length-89 sorted `locs` array from two cumulative "
        "random-walk segments (different RNG step ranges and offsets), passes it "
        "to `FixedLocator(locs, nbins=12)`, and calls `tick_values(None, None)`. "
        "That runs `matplotlib.ticker.FixedLocator.tick_values` in "
        "`lib/matplotlib/ticker.py`, which computes `step` from `nbins` and "
        "then executes `for i in range(1, step):` (header line 1803). "
        "The first statement in the loop body is line 1804. "
        "During this test run, in the **top-level** invocation of "
        "`FixedLocator.tick_values`, how many times does line 1804 execute? "
        "Return a JSON object with key `loop_iteration_count` and an integer value."
    )

    qa = {
        "question_kind": "iterations",
        "question": question,
        "template_answer": {
            "loop_iteration_count": "int",
        },
        "oracle_answer": {
            "loop_iteration_count": iteration_count,
        },
        "execution": {
            "eval_entry": "matplotlib_qa/ticker_fixedloc_rstride_loop_iterations/eval.sh",
            "trace_policy": {
                "trace_file_substr": "lib/matplotlib/ticker.py",
                "trace_func": "",
                "notes": (
                    "Fingerprints FixedLocator.tick_values via line 1801; "
                    "end of target via return line 1807."
                ),
            },
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
