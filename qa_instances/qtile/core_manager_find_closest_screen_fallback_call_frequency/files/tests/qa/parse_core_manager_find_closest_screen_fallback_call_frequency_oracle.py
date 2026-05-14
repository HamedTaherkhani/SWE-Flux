#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_FUNCS = {
    "libqtile.core.manager._find_closest_closest",
    "libqtile.core.manager.Qtile._find_closest_closest",
}
CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/core/manager\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)


def extract_call_frequency(trace_text: str) -> dict:
    call_count = 0
    for match in CALL_RE.finditer(trace_text):
        if match.group("func") in TARGET_FUNCS:
            call_count += 1
    return {"function_call_count": call_count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_find_closest_screen_fallback_call_frequency/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_find_closest_screen_fallback_call_frequency/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_frequency(trace_text)

    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/core_manager_find_closest_screen_fallback_call_frequency_test.py`, class "
            "`TestCoreManagerFindClosestScreenFallbackCallFrequencyQA`, method "
            "`test_core_manager_find_closest_screen_fallback_call_frequency_case`. "
            "At line 46 the loop over generated query points starts, and line 51 executes "
            "`screen = probe.find_closest_screen(x, y)` for each transformed coordinate. "
            "During this full test run, how many times is fallback function "
            "`libqtile.core.manager._find_closest_closest` in file `libqtile/core/manager.py` called? "
            "Use exactly that file path and fully-qualified function name to identify the target call site."
        ),
        "template_answer": {
            "function_call_count": "int"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
