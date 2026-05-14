#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/libqtile/core/manager.py"
TARGET_FUNCS = {
    "libqtile.core.manager.load_config",
    "libqtile.core.manager.Qtile.load_config",
}

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/core/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
)


def func_matches(func_name: str) -> bool:
    return any(func_name == t or func_name.startswith(f"{t}.") for t in TARGET_FUNCS)


def extract_covered_lines(trace_text: str) -> list[int]:
    covered: set[int] = set()

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if m.group("path") != TARGET_PATH:
            continue
        if not func_matches(m.group("func")):
            continue
        if m.group("event") != "line":
            continue
        covered.add(int(m.group("lineno")))

    return sorted(covered)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_direct_load_config_line_coverage_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_direct_load_config_line_coverage_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    covered_lines = extract_covered_lines(trace_text)

    qa = {
        "question_kind": "M1_IntraProceduralCFG",
        "question": (
            "Run the full test suite in "
            "`tests/qa/core_manager_direct_load_config_line_coverage_suite_test.py` "
            "(all tests in that file, 10 tests total). Focus only on "
            "`libqtile/core/manager.py`, function `libqtile.core.manager.load_config` "
            "(lines 113-190). The suite calls `load_config(initial=...)` directly under "
            "multiple synthetic core/config/state setups, including startup mode changes, "
            "scratchpad configuration, state restoration branches, and config load/validate "
            "exceptions. Which exact line numbers in the target function are covered at least "
            "once by this suite? Return a JSON object with exactly one key `covered_lines`, "
            "where the value is a sorted list of unique integers in ascending order: "
            "`{\"covered_lines\": [<int>, ...]}`."
        ),
        "template_answer": {
            "covered_lines": [],
        },
        "oracle_answer": {
            "covered_lines": covered_lines,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
