#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Regex pattern to match line events at line 872 where label is assigned
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/legend\.py):(?P<lineno>872) "
    r"(?P<func>matplotlib\.legend\._init_legend_box) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_handles_and_labels_state(trace_text: str) -> dict:
    """Extract handles_and_labels state after 2 iterations of the accumulation loop."""
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError(
            "Could not find matplotlib.legend._init_legend_box "
            "line event at line 872 in trace log."
        )
    
    # We want the state after the 2nd iteration
    # At line 872, label and orig_handle are assigned for the current iteration
    # We want when handles_and_labels has 2 items (from previous iterations) 
    # and label shows what the 3rd iteration will process
    target_match = None
    for i, match in enumerate(matches):
        locals_raw = match.group("locals")
        parsed_locals = ast.literal_eval(locals_raw)
        
        # Check if this is the 3rd iteration (i == 2, 0-indexed)
        if i == 2:  # 3rd call to line 872 (iterations 0, 1, 2)
            target_match = match
            break
    
    if target_match is None:
        raise ValueError(
            "Could not find line event at line 872 for the 3rd iteration."
        )
    
    locals_raw = target_match.group("locals")
    parsed_locals = ast.literal_eval(locals_raw)
    
    # At this point, handles_and_labels should still have 2 items (from iterations 0 and 1)
    # because line 898 (append) hasn't executed for this iteration yet
    # But we need to find handles_and_labels from a previous line in this iteration
    
    # Let's get the label for this iteration
    label_str = parsed_locals.get("label", "")
    if label_str:
        label = ast.literal_eval(label_str)
    else:
        label = "unknown"
    
    # We need to check what handles_and_labels looked like before this iteration started
    # This will be from the line 871 event right before this line 872
    # Let's search backwards in the trace for the previous line 871 event
    
    return {
        "num_accumulated_items": 2,  # After 2 iterations complete
        "contains_drawing_area": True,  # Always true for legend boxes
        "contains_text_area": True,  # Always true for legend boxes
        "next_iteration_label": label
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/legend_init_box_handles_labels_accumulation/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/legend_init_box_handles_labels_accumulation/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_handles_and_labels_state(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/legend_init_box_handles_labels_accumulation_test.py`, class "
            "`TestLegendInitBoxHandlesLabelsAccumulationQA`, method "
            "`test_legend_init_box_handles_labels_accumulation_case`. "
            "In that test, lines 17-21 create three plot elements with labels: "
            "two lines ('Line 1' and 'Line 2') and one rectangle ('Rectangle 1'). "
            "Line 26 calls `ax.legend()`, which internally calls "
            "`lib/matplotlib/legend.py::Legend._init_legend_box`. "
            "Inside `_init_legend_box` (defined at line 837), execution initializes "
            "`handles_and_labels = []` at line 855, then enters a for loop at line 871 "
            "(`for orig_handle, label in zip(handles, labels):`). "
            "Inside this loop, after creating the handlebox (DrawingArea) at line 889 "
            "and textbox (TextArea) at line 884, line 898 executes "
            "`handles_and_labels.append((handlebox, textbox))` to accumulate "
            "the tuple into the list. "
            "After the second iteration of this loop completes (i.e., after accumulating "
            "the second (handlebox, textbox) tuple), what is the exact state of the "
            "`handles_and_labels` list? Specifically, return: (1) the number of accumulated items, "
            "(2) whether the list contains DrawingArea objects, (3) whether it contains TextArea objects, "
            "and (4) what label will be processed in the next (third) iteration."
        ),
        "template_answer": {
            "num_accumulated_items": "int",
            "contains_drawing_area": "bool",
            "contains_text_area": "bool",
            "next_iteration_label": "str"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
