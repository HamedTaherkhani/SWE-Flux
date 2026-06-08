#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/lib/matplotlib/colors.py"
TARGET_FUNC = "matplotlib.colors.to_rgba"

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/lib/matplotlib/colors\.py):(?P<lineno>\d+) "
    r"(?P<func>matplotlib\.colors\.to_rgba) "
    r"event=return retval=(?P<retval>.+?) locals=\{"
)


def extract_retvals(trace_text: str) -> list[str]:
    retvals: list[str] = []
    for raw_line in trace_text.splitlines():
        m = RETURN_RE.match(raw_line)
        if not m:
            continue
        if m.group("path") != TARGET_PATH:
            continue
        if m.group("func") != TARGET_FUNC:
            continue
        retvals.append(m.group("retval"))
    return retvals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/colors_to_rgba_output_determinism/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/colors_to_rgba_output_determinism/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    retvals = extract_retvals(trace_text)

    invariant_exists = len(retvals) == 10 and len(set(retvals)) == 1

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Execute test "
            "`tests/qa/colors_to_rgba_output_determinism_test.py::"
            "TestColorsToRgbaOutputDeterminismQA::"
            "test_colors_to_rgba_output_determinism_case` "
            "exactly 10 independent times with identical inputs. In each execution, "
            "`matplotlib.colors.to_rgba` in `lib/matplotlib/colors.py` is called once with "
            "c=`'#9467bd'` (six-digit hex) and alpha=`0.625`. "
            "`to_rgba` consults and may populate an internal RGBA cache keyed by `(c, alpha)`. "
            "Is the value returned by `to_rgba` identical across all 10 executions "
            "(as recorded in the trace `retval=` string for the top-level return from "
            "`matplotlib.colors.to_rgba`)? "
            "Return JSON with exactly one key: `{\"invariant_exists\": <bool>}`."
        ),
        "template_answer": {
            "invariant_exists": "bool",
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists,
        },
        "execution": {
            "eval_entry": "matplotlib_qa/colors_to_rgba_output_determinism/eval.sh",
            "trace_policy": {
                "trace_file_substr": "lib/matplotlib/colors.py",
                "trace_func": "matplotlib.colors.to_rgba",
                "notes": (
                    "Output oracle: TRACE_EVENTS call,return; one return per run; "
                    "compare retval= strings across 10 pytest invocations."
                ),
            },
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
