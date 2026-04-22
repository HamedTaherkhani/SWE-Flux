#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Regex patterns for different lines
ISTEP_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/ticker\.py):2203 "
    r"(?P<func>matplotlib\.ticker\._raw_ticks) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

STEP_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/ticker\.py):2205 "
    r"(?P<func>matplotlib\.ticker\._raw_ticks) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

LARGE_STEPS_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/ticker\.py):2187 "
    r"(?P<func>matplotlib\.ticker\._raw_ticks) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

STEPS_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/ticker\.py):2175 "
    r"(?P<func>matplotlib\.ticker\._raw_ticks) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_step_selection_state(trace_text: str) -> dict:
    """
    Extract the state from various lines in the _raw_ticks function during step selection.
    """
    import numpy as np
    from numpy import array  # Needed for eval
    
    # Get istep from line 2203
    istep_matches = list(ISTEP_LINE_RE.finditer(trace_text))
    if not istep_matches:
        raise ValueError("Could not find istep at line 2203")
    istep_locals = eval(istep_matches[0].group("locals"))
    istep = int(eval(istep_locals["istep"]))
    
    # Get step from line 2205 (first iteration value)
    step_matches = list(STEP_LINE_RE.finditer(trace_text))
    if not step_matches:
        raise ValueError("Could not find step at line 2205")
    step_locals = eval(step_matches[0].group("locals"))
    step = float(eval(step_locals["step"]))
    
    # Get large_steps from line 2187
    large_steps_matches = list(LARGE_STEPS_LINE_RE.finditer(trace_text))
    if not large_steps_matches:
        raise ValueError("Could not find large_steps at line 2187")
    large_steps_locals = eval(large_steps_matches[0].group("locals"))
    large_steps = eval(large_steps_locals["large_steps"])
    num_large_steps = int(large_steps.sum())
    
    # Get steps array from line 2175
    steps_matches = list(STEPS_LINE_RE.finditer(trace_text))
    if steps_matches:
        steps_locals = eval(steps_matches[0].group("locals"))
        steps_str = steps_locals.get("steps", "")
        if steps_str:
            steps = eval(steps_str)
            num_steps = len(steps)
        else:
            num_steps = 0
    else:
        num_steps = 0
    
    return {
        "first_step_value": step,
        "istep_index": istep,
        "num_steps_in_array": num_steps,
        "num_large_steps": num_large_steps
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/ticker_maxn_raw_ticks_step_selection/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/ticker_maxn_raw_ticks_step_selection/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_step_selection_state(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/ticker_maxn_raw_ticks_step_selection_test.py`, class "
            "`TestTickerMaxNRawTicksStepSelectionQA`, method "
            "`test_ticker_maxn_raw_ticks_step_selection_case`. "
            "In that test, line 15 creates a MaxNLocator with `nbins=4` and "
            "`steps=[1, 2, 5, 10]`. Line 24 calls `locator._raw_ticks(12.3, 87.6)`, "
            "which internally calls `lib/matplotlib/ticker.py::MaxNLocator._raw_ticks`. "
            "Inside `_raw_ticks` (defined at line 2155), execution calculates the "
            "`steps` array at line 2174 by multiplying `self._extended_steps * scale`. "
            "At line 2177, if `self._integer` is True, steps are filtered. "
            "At line 2186, a boolean array `large_steps` is created by comparing "
            "`steps >= raw_step`. At line 2192, `large_steps` is further filtered "
            "based on round_numbers mode. At line 2196, `istep` is calculated as the "
            "index of the first True value in `large_steps`. "
            "Finally, at line 2203, a for loop begins: "
            "`for step in steps[:istep+1][::-1]:` which iterates through the steps "
            "in reverse order. When this loop FIRST begins execution (i.e., at the "
            "very start of the first iteration, when line 2205 is reached), what is: "
            "(1) the value of the first `step` variable from the iteration, "
            "(2) the value of `istep`, (3) the total number of elements in the `steps` "
            "array (from line 2174), and (4) how many True values are in the "
            "`large_steps` boolean array (from line 2187)?"
        ),
        "template_answer": {
            "first_step_value": "float",
            "istep_index": "int",
            "num_steps_in_array": "int",
            "num_large_steps": "int"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
