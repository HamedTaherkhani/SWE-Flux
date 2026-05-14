#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/libqtile/backend/x11/(?:core|window)\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.backend\.x11\.(?:core\.(?:_xpoll|handle_event)|window\.(?:get_wm_type|get_property))) "
    r"event=line ",
    re.MULTILINE,
)


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for backend x11 multi-file execution path extraction.")

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
            "backend_x11_core_poll_multi_file_execution_path_lines/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "backend_x11_core_poll_multi_file_execution_path_lines/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_execution_path(trace_text)

    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/backend_x11_core_poll_multi_file_execution_path_lines_test.py`, "
            "class `TestBackendX11CorePollMultiFileExecutionPathLinesQA`, method "
            "`test_backend_x11_core_poll_multi_file_execution_path_lines_case`. "
            "This is a direct backend test centered on `Core._xpoll` in `libqtile/backend/x11/core.py`, "
            "with chained calls into `XWindow.get_wm_type` and `XWindow.get_property` in "
            "`libqtile/backend/x11/window.py`. The event stream includes motion, enter, leave, "
            "button-press, and generic events; target-chain handlers call into the window methods "
            "multiple times with mixed property-reply outcomes (valid atoms, empty values, and caught backend errors). "
            "Return the execution path only for line events from these files and functions: "
            "`libqtile/backend/x11/core.py` with funcs `libqtile.backend.x11.core._xpoll`, "
            "`libqtile.backend.x11.core.handle_event`; and `libqtile/backend/x11/window.py` with funcs "
            "`libqtile.backend.x11.window.get_wm_type`, `libqtile.backend.x11.window.get_property`. "
            "Formatting requirement: each `file` must be repo-relative POSIX path format "
            "`libqtile/backend/x11/<module>.py`; each `func` must be fully-qualified function-name format "
            "`libqtile.backend.x11.<module>.<function>` (no class names, no abbreviations). "
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
