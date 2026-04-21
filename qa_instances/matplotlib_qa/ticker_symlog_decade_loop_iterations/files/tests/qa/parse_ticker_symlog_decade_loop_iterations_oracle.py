#!/usr/bin/env python3
"""
Parse execution trace for SymmetricalLogLocator.tick_values: count iterations of
`for decade in decades:` (loop body line 2641 in lib/matplotlib/ticker.py).

Python 3.10 traces methods as matplotlib.ticker.tick_values (no class in the
name), so we fingerprint SymmetricalLogLocator via line 2594
(`has_a = (vmin < -linthresh)`), then count body line 2641 until the matching
`tick_values` returns (line 2648).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/lib/matplotlib/ticker.py"
FP_LINE_SYML_TICK_VALUES = 2594  # has_a = (vmin < -linthresh)
LOOP_BODY_LINE = 2641  # if decade == 0:
RETURN_LINE = 2648  # return self.raise_if_exceeds(...)

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} (?P<path>/testbed[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _is_tick_values_func(func: str) -> bool:
    return func.endswith(".tick_values")


def count_decade_loop_iterations(trace_text: str) -> int:
    tv_depth = 0
    symlog_active = False
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
            symlog_active = False
            continue

        if event in ("return", "exception") and _is_tick_values_func(func):
            if symlog_active and tv_depth >= 1 and lineno == RETURN_LINE:
                symlog_active = False
            if tv_depth >= 1:
                tv_depth -= 1
            continue

        if event != "line":
            continue

        if not _is_tick_values_func(func):
            continue

        if tv_depth < 1:
            continue

        if lineno == FP_LINE_SYML_TICK_VALUES:
            symlog_active = True
            continue

        if symlog_active and lineno == LOOP_BODY_LINE:
            count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/ticker_symlog_decade_loop_iterations/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/ticker_symlog_decade_loop_iterations/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    iteration_count = count_decade_loop_iterations(trace_text)

    question = (
        "Use `tests/qa/ticker_symlog_decade_loop_iterations_test.py`, class "
        "`TestTickerSymlogDecadeLoopIterationsQA`, method "
        "`test_ticker_symlog_decade_loop_iterations_case`. "
        "The test constructs a `SymmetricalLogLocator` with `linthresh=0.5`, "
        "`base=10`, `subs=(1.0, 2.0, 5.0)`, sets `numticks` to `9`, and calls "
        "`tick_values(-2000.0, 8000.0)`. That executes "
        "`matplotlib.ticker.SymmetricalLogLocator.tick_values` in "
        "`lib/matplotlib/ticker.py`, which partitions the domain into negative "
        "quasi-log decades, an optional linear band around zero, and positive "
        "decades; applies stride-based thinning to limit tick count; then, "
        "when subs imply non-unity factors, builds `ticklocs` inside the loop "
        "`for decade in decades:` (the loop header is at line 2640; the first "
        "statement of the loop body is line 2641). "
        "During this test run, in the **top-level** invocation of "
        "`SymmetricalLogLocator.tick_values` (not nested helper calls), how many "
        "times does that loop body line (line 2641) execute? "
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
            "eval_entry": "matplotlib_qa/ticker_symlog_decade_loop_iterations/eval.sh",
            "trace_policy": {
                "trace_file_substr": "lib/matplotlib/ticker.py",
                "trace_func": "",
                "notes": (
                    "Full-file line tracing inside ticker.py for the test window; "
                    "parser fingerprints SymmetricalLogLocator.tick_values via line 2594."
                ),
            },
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
