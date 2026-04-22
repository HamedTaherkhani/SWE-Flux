#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/libqtile/core/(?:manager|state)\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.core\.(?:manager\.(?:Qtile\.)?(?:reload_config|_finalize_configurables)|state\.(?:QtileState\.)?__init__)) "
    r"event=line ",
    re.MULTILINE,
)


def _normalize_func(func: str) -> str:
    normalized = func.replace("libqtile.core.manager.Qtile.", "libqtile.core.manager.")
    normalized = normalized.replace("libqtile.core.state.QtileState.", "libqtile.core.state.")
    return normalized


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError(
            "Could not find line events for reload_config/_finalize_configurables/state.__init__ path extraction."
        )

    executed_path = []
    for m in matches:
        executed_path.append(
            {
                "file": m.group("path").replace("/testbed/", ""),
                "func": _normalize_func(m.group("func")),
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
            "core_manager_reload_config_finalize_execution_path_lines/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_reload_config_finalize_execution_path_lines/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_execution_path(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `tests/qa/core_manager_reload_config_finalize_execution_path_lines_test.py`, class "
            "`TestCoreManagerReloadConfigFinalizeExecutionPathLinesQA`, method "
            "`test_core_manager_reload_config_finalize_execution_path_lines_case`. "
            "This is a direct core test of `Qtile.reload_config` in `libqtile/core/manager.py`, "
            "with chained execution through `QtileState.__init__` in `libqtile/core/state.py` and "
            "`Qtile._finalize_configurables` back in `manager.py`. "
            "Return the execution path only for line events from the following files/functions: "
            "`libqtile/core/manager.py` with funcs `libqtile.core.manager.reload_config`, "
            "`libqtile.core.manager._finalize_configurables`; and `libqtile/core/state.py` with func "
            "`libqtile.core.state.__init__`. "
            "Formatting requirement: each `file` must be repo-relative POSIX path like "
            "`libqtile/core/<module>.py`; each `func` must be fully-qualified in module-function format "
            "exactly like `libqtile.core.manager.reload_config` or `libqtile.core.state.__init__` "
            "(no class-name segments, no abbreviations). "
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
