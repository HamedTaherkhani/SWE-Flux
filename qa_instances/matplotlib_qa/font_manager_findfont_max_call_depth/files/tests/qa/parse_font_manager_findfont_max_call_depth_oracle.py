#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from collections import defaultdict

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/.*?):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|return|exception)",
    re.MULTILINE,
)


def compute_max_call_depth(trace_text: str) -> dict:
    """
    Compute the maximum call stack depth from trace log.
    Only count events from files under /testbed/lib/matplotlib/.
    Track call/return events to maintain accurate stack depth.
    """
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find any traced events for call depth calculation.")
    
    # Track the call stack using a simple counter
    # Each 'call' increments, each 'return' or 'exception' decrements
    current_depth = 0
    max_depth = 0
    
    for match in matches:
        event = match.group("event")
        
        if event == "call":
            current_depth += 1
            if current_depth > max_depth:
                max_depth = current_depth
        elif event in ("return", "exception"):
            current_depth = max(0, current_depth - 1)
    
    return {"maximum_call_stack_depth": max_depth}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/font_manager_findfont_max_call_depth/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/font_manager_findfont_max_call_depth/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = compute_max_call_depth(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `tests/qa/font_manager_findfont_max_call_depth_test.py`, class "
            "`TestFontManagerFindfontMaxCallDepthQA`, method "
            "`test_font_manager_findfont_max_call_depth_case`. "
            "This test performs three complex findfont operations with multiple generic font families "
            "(sans-serif, serif, monospace, cursive, fantasy) and different style/weight combinations. "
            "Each findfont call triggers: (1) FontProperties expansion of generic families via rcParams, "
            "(2) iteration through the font list with repeated calls to score_family, score_weight, "
            "score_style, score_stretch, score_variant, and score_size for each candidate font, "
            "(3) potential cache lookups and property conversions. "
            "Compute call stack depth over the scope `/testbed/lib/matplotlib/` (i.e., all traced "
            "call/return/exception events from files under this directory, excluding Python/internal library frames). "
            "What is the maximum call stack depth reached during the entire execution of this test run?"
        ),
        "template_answer": {
            "maximum_call_stack_depth": "int"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
