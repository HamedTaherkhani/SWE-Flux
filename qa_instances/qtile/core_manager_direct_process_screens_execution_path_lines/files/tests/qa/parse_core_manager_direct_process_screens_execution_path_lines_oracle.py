#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/core/manager\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.core\.manager\.(?:Qtile\.)?_process_screens) "
    r"event=line ",
    re.MULTILINE,
)


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for _process_screens execution path extraction.")

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
            "core_manager_direct_process_screens_execution_path_lines/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_direct_process_screens_execution_path_lines/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_execution_path(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `tests/qa/core_manager_direct_process_screens_execution_path_lines_test.py`, "
            "class `TestCoreManagerDirectProcessScreensExecutionPathLinesQA`, method "
            "`test_core_manager_direct_process_screens_execution_path_lines_case`. "
            "This is a direct core test of `Qtile._process_screens` in `libqtile/core/manager.py` "
            "(function starts at line 364 and contains multiple loops and nested conditionals). "
            "The test patches `manager.Screen` and `manager.bar.Bar` with stubs, sets `reloading=True`, "
            "uses duplicated backend screen coordinates, pre-populates two old screens with bar gaps, "
            "and provides three configured screens so both configured-screen and auto-screen creation paths execute. "
            "Return the execution path only for line events from `libqtile/core/manager.py` and only for "
            "function `libqtile.core.manager._process_screens`. "
            "Formatting requirement: in every path object, `file` must be exactly "
            "`libqtile/core/manager.py` (repo-relative path), and `func` must be exactly "
            "`libqtile.core.manager._process_screens` (fully-qualified function name). "
            "Do not abbreviate or shorten these strings. "
            "What is the exact ordered execution path as a list of objects with keys `file`, `func`, and `line`, "
            "including repeated lines?"
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
