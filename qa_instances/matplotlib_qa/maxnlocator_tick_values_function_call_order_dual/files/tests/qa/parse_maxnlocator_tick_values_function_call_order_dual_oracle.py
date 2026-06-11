#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/ticker\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)

ALLOWED = {
    "matplotlib.ticker._staircase",
    "matplotlib.ticker.tick_values",
    "matplotlib.ticker._raw_ticks",
    "matplotlib.ticker.scale_range",
    "matplotlib.ticker.le",
    "matplotlib.ticker.ge",
    "matplotlib.ticker.raise_if_exceeds",
}


def extract_call_order(trace_text: str) -> dict:
    function_call_order = []
    for m in CALL_RE.finditer(trace_text):
        func = m.group("func")
        if func not in ALLOWED:
            continue
        if "<locals>" in func:
            continue
        function_call_order.append(
            {
                "file": m.group("path").replace("/testbed/", ""),
                "func": func,
            }
        )
    if not function_call_order:
        raise ValueError("No matching ticker.py call events for function_call_order extraction.")
    return {"function_call_order": function_call_order}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/maxnlocator_tick_values_function_call_order_dual/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/maxnlocator_tick_values_function_call_order_dual/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_order(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `tests/qa/maxnlocator_tick_values_function_call_order_dual_test.py`, class "
            "`TestMaxnlocatorTickValuesFunctionCallOrderDualQA`, method "
            "`test_maxnlocator_tick_values_function_call_order_dual_case`. "
            "The test constructs `matplotlib.ticker.MaxNLocator(nbins=5, integer=False, steps=[1, 2, 5, 10])` "
            "and calls `tick_values(10.0, 99.0)`, then constructs "
            "`MaxNLocator(nbins=8, integer=True, min_n_ticks=3)` and calls `tick_values(11, 107)`. "
            "Return the exact ordered sequence of function calls only for file `lib/matplotlib/ticker.py` "
            "and only for these functions: `matplotlib.ticker._staircase`, `matplotlib.ticker.tick_values`, "
            "`matplotlib.ticker._raw_ticks`, `matplotlib.ticker.scale_range`, `matplotlib.ticker.le`, "
            "`matplotlib.ticker.ge`, and `matplotlib.ticker.raise_if_exceeds`. "
            "What is the exact ordered sequence of function calls as a list of objects with keys `file` and "
            "`func`, including repeated calls?"
        ),
        "template_answer": {
            "function_call_order": [
                {
                    "file": "str",
                    "func": "str",
                }
            ]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
