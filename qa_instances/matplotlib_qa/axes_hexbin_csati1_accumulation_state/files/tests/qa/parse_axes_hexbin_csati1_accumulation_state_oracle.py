#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Regex pattern to match line events at line 5226 (start of for loop)
# We want to capture when i transitions from 2 to 3, showing Cs_at_i1 state after 3 iterations
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/axes/_axes\.py):(?P<lineno>5226) "
    r"(?P<func>matplotlib\.axes\._axes\.(?:hexbin|<listcomp>)) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_csati1_state(trace_text: str) -> dict:
    """Extract Cs_at_i1 state after 3 iterations of the accumulation loop."""
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError(
            "Could not find line events at line 5226 in trace log."
        )
    
    # Find the line event at 5226 where Cs_at_i1 is visible and appears right
    # before i=3 (meaning iterations 0, 1, 2 have completed)
    target_match = None
    for i, match in enumerate(matches):
        locals_raw = match.group("locals")
        parsed_locals = ast.literal_eval(locals_raw)
        
        # Look for the match that has Cs_at_i1 with accumulated values
        # We want the one right before the loop continues to i=3
        if "Cs_at_i1" in parsed_locals:
            csati1_str = parsed_locals["Cs_at_i1"]
            # Check if this Cs_at_i1 has the pattern we expect after i=2
            # It should have values at positions 1 and 8 based on the trace
            if "[np.float64(30.0)]" in csati1_str:
                # This is likely after i=2 completes
                target_match = match
                break
    
    if target_match is None:
        raise ValueError(
            "Could not find line event at line 5226 with Cs_at_i1 state after i=2."
        )
    
    locals_raw = target_match.group("locals")
    parsed_locals = ast.literal_eval(locals_raw)
    
    if "Cs_at_i1" not in parsed_locals:
        raise ValueError(
            "Line event does not include 'Cs_at_i1' in locals."
        )
    
    # Parse Cs_at_i1 from the string representation
    csati1_str = parsed_locals["Cs_at_i1"]
    # This contains numpy types like np.float64(), so we need to use eval with numpy
    import numpy as np
    Cs_at_i1 = eval(csati1_str)
    
    # Return which indices have values and what those values are
    non_empty = {}
    for idx, sublist in enumerate(Cs_at_i1):
        if sublist:  # non-empty
            # Convert numpy floats to regular floats
            non_empty[str(idx)] = [float(v) for v in sublist]
    
    return {
        "non_empty_indices": sorted([int(k) for k in non_empty.keys()]),
        "accumulated_values": non_empty
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/axes_hexbin_csati1_accumulation_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/axes_hexbin_csati1_accumulation_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_csati1_state(trace_text)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `tests/qa/axes_hexbin_csati1_accumulation_state_test.py`, class "
            "`TestAxesHexbinCsati1AccumulationStateQA`, method "
            "`test_axes_hexbin_csati1_accumulation_state_case`. "
            "In that test, lines 13-15 define test data arrays "
            "`x = np.array([0.5, 1.5, 2.5, 0.8, 1.2, 2.8])`, "
            "`y = np.array([0.5, 1.5, 2.5, 1.8, 0.8, 1.2])`, and "
            "`C = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])`. "
            "Line 21 calls `ax.hexbin(x, y, C=C, gridsize=3, reduce_C_function=np.mean)`. "
            "Inside `lib/matplotlib/axes/_axes.py::Axes.hexbin` (the method starts around line 4981), "
            "execution reaches the else branch at line 5222 where `C is not None`. "
            "At line 5224, `Cs_at_i1 = [[] for _ in range(1 + nx1 * ny1)]` initializes a list of empty lists. "
            "Then the for loop at line 5226 (`for i in range(len(x))`) iterates through each data point. "
            "Inside this loop, line 5227 checks `if bdist[i]:`, and if True, line 5228 executes "
            "`Cs_at_i1[i1[i]].append(C[i])` to accumulate the C value into the appropriate sublist. "
            "After the first 3 iterations (i=0, i=1, i=2) of this loop complete, "
            "what is the exact state of the `Cs_at_i1` list structure? "
            "Specifically, return which indices contain non-empty sublists and what values they contain."
        ),
        "template_answer": {
            "non_empty_indices": ["int"],
            "accumulated_values": {
                "int_key": ["float"]
            }
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
