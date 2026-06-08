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


def _condition_line(source_text: str) -> int:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_eagerly_encode_cf_datetime":
            fn = node
            break
    if fn is None:
        raise ValueError("_eagerly_encode_cf_datetime not found.")

    for node in ast.walk(fn):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
                if isinstance(test.ops[0], ast.Gt):
                    if (
                        isinstance(test.left, ast.Name)
                        and test.left.id == "time_delta"
                        and isinstance(test.comparators[0], ast.Name)
                        and test.comparators[0].id == "needed_time_delta"
                    ):
                        return node.lineno
    raise ValueError("Target condition `if time_delta > needed_time_delta` not found.")


def extract_snapshot(trace_text: str, source_text: str) -> dict[str, str]:
    cond_line = _condition_line(source_text)
    cached_time_delta: str | None = None
    cached_needed: str | None = None

    for m in LINE_RE.finditer(trace_text):
        if not m.group("func").endswith("._eagerly_encode_cf_datetime"):
            continue

        locals_map = ast.literal_eval(m.group("locals"))
        if "time_delta" in locals_map:
            cached_time_delta = str(locals_map["time_delta"])
        if "needed_time_delta" in locals_map:
            cached_needed = str(locals_map["needed_time_delta"])

        if int(m.group("lineno")) != cond_line:
            continue

        if cached_time_delta is not None and cached_needed is not None:
            return {
                "x": cached_time_delta,
                "threshold": cached_needed,
            }

    raise ValueError("Could not capture locals at target conditional line.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/cf_time_delta_condition_snapshot/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/coding/times.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/cf_time_delta_condition_snapshot/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_snapshot(trace_text, source_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Run `xarray/tests/qa/cf_time_delta_condition_snapshot_test.py`, class "
            "`TestCFTimeDeltaConditionSnapshotHardQA`, method "
            "`test_cf_time_delta_condition_snapshot_case`. In "
            "`xarray/coding/times.py`, inside `_eagerly_encode_cf_datetime`, inspect the "
            "condition `if time_delta > needed_time_delta:`. What are the exact runtime values "
            "of `time_delta` (x) and `needed_time_delta` (threshold) at the moment this "
            "condition is evaluated?"
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
