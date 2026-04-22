#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_LINE = 115
TARGET_FUNC = "libqtile.scripts.top.get_stats"
TARGET_PATH = "/testbed/libqtile/scripts/top.py"

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/libqtile/scripts/top\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>\w+).*? locals=(?P<locals>\{.*\})$"
)


def extract_total_values(trace_text: str) -> list[int]:
    values: list[int] = []
    for line in trace_text.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue

        if m.group("path") != TARGET_PATH:
            continue
        if m.group("func") != TARGET_FUNC:
            continue
        if m.group("event") != "line":
            continue
        if int(m.group("lineno")) != TARGET_LINE:
            continue

        try:
            local_map = ast.literal_eval(m.group("locals"))
        except Exception:
            continue

        if "total" not in local_map:
            continue

        try:
            values.append(int(local_map["total"]))
        except Exception:
            continue

    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "scripts_top_direct_get_stats_total_value_range_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "scripts_top_direct_get_stats_total_value_range_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    totals = extract_total_values(trace_text)

    if not totals:
        raise RuntimeError("No observed values found for variable 'total'.")

    qa = {
        "question_kind": "value_range_analysis",
        "question": (
            "Use the full test suite in `tests/qa/scripts_top_direct_get_stats_total_value_range_suite_test.py` "
            "(all generated test cases in class `TestScriptsTopDirectGetStatsTotalValueRangeSuiteQA`, 15 tests). "
            "Focus only on function `libqtile.scripts.top.get_stats` in file `libqtile/scripts/top.py`. "
            "At line `115`, use local variable `total` (computed at line `114`). "
            "Across all executions of that line over the full suite, what is the inclusive numeric range "
            "of `total`? Return JSON with exactly these keys: `variable`, `min_value`, `max_value`."
        ),
        "template_answer": {
            "variable": "str",
            "min_value": "int",
            "max_value": "int",
        },
        "oracle_answer": {
            "variable": "total",
            "min_value": min(totals),
            "max_value": max(totals),
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
