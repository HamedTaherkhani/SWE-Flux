#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
import numpy as np

TARGET_PATH = "/testbed/lib/matplotlib/cbook.py"
TARGET_FUNC = "matplotlib.cbook.boxplot_stats"
TARGET_LINE = 1248

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
            np_pattern = r"np\.(float64|int64|float32|int32)\(([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\)"
            match = re.match(np_pattern, value)
            if match:
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
        # At line 1248: stats['iqr'] = q3 - q1
        # Check the invariant: before this assignment, q1 <= q3 should hold
        if "q1" not in current or "q3" not in current:
            continue
        
        q1 = current["q1"]
        q3 = current["q3"]
        if not isinstance(q1, (int, float)) or not isinstance(q3, (int, float)):
            continue
        
        # Handle NaN cases
        if np.isnan(q1) or np.isnan(q3):
            continue
        
        seen_any = True
        # The invariant: q1 <= q3 (by definition of percentiles)
        invariant = q1 <= q3
        if not invariant:
            invariant_holds_for_all = False

    return {"invariant_exists": seen_any and invariant_holds_for_all}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "cbook_boxplot_q1_le_q3_invariant_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "cbook_boxplot_q1_le_q3_invariant_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_invariant(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in "
            "`tests/qa/cbook_boxplot_q1_le_q3_invariant_suite_test.py` "
            "(all test cases in class "
            "`TestCbookBoxplotQ1LeQ3InvariantSuiteQA`, 25 tests). "
            "Each test calls `boxplot_stats([data])` with different statistical distributions. "
            "Focus on `lib/matplotlib/cbook.py`, function "
            "`matplotlib.cbook.boxplot_stats`. "
            "At line `1248` (`stats['iqr'] = q3 - q1`), consider local variables `q1` and `q3`. "
            "These are computed at line 1245 as `q1, med, q3 = np.percentile(x, [25, 50, 75])`. "
            "Across all evaluations of line 1248 over the full suite (including multiple loop "
            "iterations when X has multiple columns), is the property `q1 <= q3` an invariant property? "
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
