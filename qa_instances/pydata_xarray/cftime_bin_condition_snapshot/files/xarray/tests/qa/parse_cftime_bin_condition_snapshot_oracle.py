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
CF_DATETIME_RE = re.compile(r"cftime\.[A-Za-z_]\w*\([^)]*\)")
INT_RE = re.compile(r"-?\d+")
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


def _target_condition_lineno(source_text: str) -> int:
    tree = ast.parse(source_text)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "CFTimeGrouper":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "first_items":
                    for candidate in ast.walk(item):
                        if isinstance(candidate, ast.If):
                            test_expr = ast.unparse(candidate.test).replace(" ", "")
                            if test_expr == "index[-1]>datetime_bins[-1]":
                                return candidate.lineno
    raise ValueError("Target condition `if index[-1] > datetime_bins[-1]` not found.")


def _extract_last_cftime_datetime(value_repr: str) -> str:
    ts_matches = TS_RE.findall(value_repr)
    if ts_matches:
        return ts_matches[-1]

    matches = CF_DATETIME_RE.findall(value_repr)
    if not matches:
        raise ValueError(f"No cftime datetime literal found in: {value_repr!r}")
    dt_literal = matches[-1]
    nums = [int(x) for x in INT_RE.findall(dt_literal)]
    if len(nums) < 3:
        raise ValueError(f"Could not parse datetime components from: {dt_literal!r}")

    year, month, day = nums[0], nums[1], nums[2]
    hour = nums[3] if len(nums) > 3 else 0
    minute = nums[4] if len(nums) > 4 else 0
    second = nums[5] if len(nums) > 5 else 0
    return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"


def extract_snapshot(trace_text: str, source_text: str) -> dict[str, str]:
    target_lineno = _target_condition_lineno(source_text)
    cached_index: str | None = None
    cached_datetime_bins: str | None = None

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        lineno = int(m.group("lineno"))
        if not func.endswith(".first_items"):
            continue

        locals_map = ast.literal_eval(m.group("locals"))
        if "index" in locals_map:
            cached_index = locals_map["index"]
        if "datetime_bins" in locals_map:
            cached_datetime_bins = locals_map["datetime_bins"]

        if lineno == target_lineno and cached_index is not None and cached_datetime_bins is not None:
            x_value = _extract_last_cftime_datetime(cached_index)
            threshold_value = _extract_last_cftime_datetime(cached_datetime_bins)
            return {"x": x_value, "threshold": threshold_value}

    raise ValueError("Could not capture locals at target conditional line.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/cftime_bin_condition_snapshot/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/resample_cftime.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/cftime_bin_condition_snapshot/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_snapshot(trace_text, source_text)

    qa = {
        "question_kind": "conditional_statements",
        "question": (
            "Use `xarray/tests/qa/cftime_bin_condition_snapshot_test.py`, class "
            "`TestCFTimeBinConditionSnapshotHardQA`, method "
            "`test_cftime_bin_condition_snapshot_case`. "
            "During that test, execution enters `xarray/core/resample_cftime.py::CFTimeGrouper.first_items`. "
            "At the conditional statement `if index[-1] > datetime_bins[-1]:`, what are the exact runtime values "
            "of `index[-1]` and `datetime_bins[-1]` at the moment this condition is evaluated? "
            "Return them as fields `x` and `threshold` in `YYYY-MM-DD HH:MM:SS` format."
        ),
        "template_answer": {
            "x": "str",
            "threshold": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
