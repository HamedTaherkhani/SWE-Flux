#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/lib/matplotlib/streamplot\.py:\d+ "
    r"matplotlib\.streamplot\.interpgrid event=call ",
    re.MULTILINE,
)


def count_interpgrid_calls(trace_text: str) -> dict:
    n = len(CALL_RE.findall(trace_text))
    if n == 0:
        raise ValueError(
            "No traced calls for matplotlib.streamplot.interpgrid; "
            "check TRACE_FILE, TRACE_FUNC, and trace log path."
        )
    return {"function_call_count": n}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/streamplot_rotating_interpgrid_call_frequency/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/streamplot_rotating_interpgrid_call_frequency/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = count_interpgrid_calls(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `tests/qa/streamplot_rotating_interpgrid_call_frequency_test.py`, class "
            "`TestStreamplotRotatingInterpgridCallFrequencyQA`, method "
            "`test_streamplot_rotating_interpgrid_call_frequency_case`. "
            "The test builds a 10x10 grid on [-2, 2]^2 with a rotating velocity field "
            "U = -Y, V = X and calls `Axes.streamplot` with `density=0.8` and "
            "`broken_streamlines=True`. "
            "During streamline integration, the velocity field is sampled through "
            "`matplotlib.streamplot.interpgrid` (bilinear interpolation on the staggered grids). "
            "Count only traced `event=call` lines for the qualified name "
            "`matplotlib.streamplot.interpgrid` in file `lib/matplotlib/streamplot.py`. "
            "During the entire test run, how many times is that function called?"
        ),
        "template_answer": {
            "function_call_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
