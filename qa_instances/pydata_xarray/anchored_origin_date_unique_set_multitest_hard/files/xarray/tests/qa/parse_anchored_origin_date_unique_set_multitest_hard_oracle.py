#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)
INT_RE = re.compile(r"-?\d+")


def _target_line(source_text: str) -> int:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_adjust_dates_anchored":
            fn = node
            break
    if fn is None:
        raise ValueError("_adjust_dates_anchored not found.")

    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "foffset" for t in node.targets):
                return node.lineno
    raise ValueError("Could not find `foffset` assignment line.")


def _normalize_cftime_datetime(value_repr: str) -> str:
    nums = [int(x) for x in INT_RE.findall(value_repr)]
    if len(nums) < 3:
        raise ValueError(f"Cannot parse datetime from: {value_repr!r}")
    year, month, day = nums[0], nums[1], nums[2]
    hour = nums[3] if len(nums) > 3 else 0
    minute = nums[4] if len(nums) > 4 else 0
    second = nums[5] if len(nums) > 5 else 0
    return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"


def extract_unique_values(trace_text: str, source_text: str) -> dict[str, object]:
    target_lineno = _target_line(source_text)
    unique_vals: set[str] = set()

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        lineno = int(m.group("lineno"))
        if lineno != target_lineno or not func.endswith("._adjust_dates_anchored"):
            continue
        locals_map = ast.literal_eval(m.group("locals"))
        if "origin_date" not in locals_map:
            continue
        unique_vals.add(_normalize_cftime_datetime(locals_map["origin_date"]))

    if not unique_vals:
        raise ValueError("No `origin_date` values captured at target line.")

    return {
        "variable": "origin_date",
        "unique_values": sorted(unique_vals),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/anchored_origin_date_unique_set_multitest_hard/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/resample_cftime.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/anchored_origin_date_unique_set_multitest_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_unique_values(trace_text, source_text)

    qa = {
        "question_kind": "value_range_analysis",
        "question": (
            "Use `xarray/tests/qa/anchored_origin_date_unique_set_multitest_hard_test.py`, class "
            "`TestAnchoredOriginDateUniqueSetMultitestHardQA`, and run the full suite in that file "
            "(both test methods). During this suite, in `xarray/core/resample_cftime.py::"
            "_adjust_dates_anchored`, focus on the variable `origin_date` right before the line "
            "`foffset = (first - origin_date) % freq.as_timedelta()` executes. "
            "List all unique values taken by `origin_date` across the full suite. "
            "Return them as normalized strings in `YYYY-MM-DD HH:MM:SS` format."
        ),
        "template_answer": {
            "variable": "str",
            "unique_values": ["str"],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
