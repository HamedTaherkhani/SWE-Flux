#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
import numpy as np

TARGET_PATH = "/testbed/lib/matplotlib/cbook.py"
TARGET_FUNC = "matplotlib.cbook.violin_stats"
TARGET_LINE = 1500

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _parse_changed_locals(raw_line: str) -> dict[str, object]:
    marker = " locals="
    index = raw_line.find(marker)
    if index < 0:
        return {}
    raw_locals = raw_line[index + len(marker):].strip()
    try:
        parsed = ast.literal_eval(raw_locals)
    except (SyntaxError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}

    decoded: dict[str, object] = {}
    for key, value in parsed.items():
        if isinstance(value, str):
            # Handle np.float64(...) or np.int64(...) patterns
            np_pattern = r"np\.(float64|int64|int16|float32|int32)\(([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\)"
            match = re.match(np_pattern, value)
            if match:
                if 'int' in match.group(1):
                    decoded[key] = int(float(match.group(2)))
                else:
                    decoded[key] = float(match.group(2))
                continue
            
            try:
                decoded[key] = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                decoded[key] = value
        else:
            decoded[key] = value
    return decoded


def extract_invariant(trace_text: str) -> dict[str, bool]:
    # Keep a per-invocation locals snapshot for the target function
    frame_stack: list[dict[str, object]] = []
    seen_any = False
    invariant_holds_for_all = True

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if m.group("path") != TARGET_PATH or m.group("func") != TARGET_FUNC:
            continue

        event = m.group("event")
        lineno = int(m.group("lineno"))

        if event == "call":
            frame_stack.append({})
            continue

        if event in {"return", "exception"}:
            if frame_stack:
                frame_stack.pop()
            continue

        if event != "line" or not frame_stack:
            continue

        changed = _parse_changed_locals(raw_line)
        if changed:
            frame_stack[-1].update(changed)

        if lineno != TARGET_LINE:
            continue

        current = frame_stack[-1]
        # At line 1500: max_val = np.max(x)
        # Check invariant: min_val <= max_val
        if "min_val" not in current or "max_val" not in current:
            continue
        
        min_val = current["min_val"]
        max_val = current["max_val"]
        
        # Handle different numeric types
        if isinstance(min_val, str):
            try:
                min_val = float(min_val)
            except:
                continue
        if isinstance(max_val, str):
            try:
                max_val = float(max_val)
            except:
                continue
        
        if not isinstance(min_val, (int, float, np.number)):
            continue
        if not isinstance(max_val, (int, float, np.number)):
            continue
        
        seen_any = True
        # Check invariant: min_val <= max_val (mathematically guaranteed for any array)
        invariant = min_val <= max_val
        if not invariant:
            invariant_holds_for_all = False

    return {"invariant_exists": seen_any and invariant_holds_for_all}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "cbook_violin_min_max_invariant_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "cbook_violin_min_max_invariant_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_invariant(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in "
            "`tests/qa/cbook_violin_min_max_invariant_suite_test.py` "
            "(all test cases in class "
            "`TestCbookViolinMinMaxInvariantSuiteQA`, 24 tests). "
            "Each test calls `violin_stats(data, method)` with different statistical distributions. "
            "Focus on `lib/matplotlib/cbook.py`, function "
            "`matplotlib.cbook.violin_stats`. "
            "At line `1500` (`max_val = np.max(x)`), after this assignment completes, "
            "consider local variables `min_val` (computed at line 1499 as `min_val = np.min(x)`) "
            "and `max_val`. "
            "These variables represent the minimum and maximum values of the input array `x` "
            "for each column of data processed in the for loop (line 1494). "
            "Across all evaluations of line 1500 over the full suite (including multiple loop "
            "iterations when data has multiple columns), is the property `min_val <= max_val` "
            "an invariant property? "
            "Return JSON as `{\\\"invariant_exists\\\": <bool>}` where `true` means the property "
            "holds for every evaluation and `false` means it does not hold."
        ),
        "template_answer": {
            "invariant_exists": "bool"
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
