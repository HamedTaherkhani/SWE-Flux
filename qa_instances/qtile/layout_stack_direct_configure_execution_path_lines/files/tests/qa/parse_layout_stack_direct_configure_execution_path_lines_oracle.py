#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/layout/stack\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.layout\.stack\.(?:Stack\.)?configure) "
    r"event=line ",
    re.MULTILINE,
)


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for Stack.configure execution path extraction.")

    executed_path = []
    for m in matches:
        executed_path.append(
            {
                "file": m.group("path").replace("/testbed/", ""),
                "func": m.group("func"),
                "line": int(m.group("lineno")),
            }
        )

    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "layout_stack_direct_configure_execution_path_lines/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "layout_stack_direct_configure_execution_path_lines/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_execution_path(trace_text)

    qa = {
        "question_kind": "C1_IntraProceduralCFG",
        "question": (
            "Use `tests/qa/layout_stack_direct_configure_execution_path_lines_test.py`, class "
            "`TestLayoutStackDirectConfigureExecutionPathLinesQA`, method "
            "`test_layout_stack_direct_configure_execution_path_lines_case`. "
            "This is a direct layout test of `Stack.configure` in `libqtile/layout/stack.py` "
            "(function starts at line 221 and has nested loop and conditional branches). "
            "The test first calls `configure` with an outsider window (not present in any stack), "
            "then calls `configure` again for `w5` in stack index 2 with `split=True` and `has_focus=False`. "
            "Return the execution path only for line events from `libqtile/layout/stack.py` and only for "
            "function `libqtile.layout.stack.configure`. "
            "Formatting requirement: each `file` must use repo-relative POSIX path format exactly like "
            "`libqtile/layout/stack.py`; each `func` must use fully-qualified function-name format exactly like "
            "`libqtile.layout.stack.configure` (no class names, no abbreviations). "
            "What is the exact ordered execution path as a list of objects with keys `file`, `func`, and `line`, "
            "including repeated lines from both calls?"
        ),
        "template_answer": {
            "executed_path": [
                {
                    "file": "str",
                    "func": "str",
                    "line": "int",
                }
            ]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
