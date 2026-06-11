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

TARGET_VARS = {"dtype_", "fill_value"}


def _collect_du_pairs(source_text: str) -> list[tuple[str, int, int]]:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "maybe_promote":
            fn = node
            break
    if fn is None:
        raise ValueError("maybe_promote not found.")

    def_lines: dict[str, set[int]] = {v: set() for v in TARGET_VARS}
    use_lines: dict[str, set[int]] = {v: set() for v in TARGET_VARS}

    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in TARGET_VARS:
                    def_lines[t.id].add(node.lineno)
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) and sub.id in TARGET_VARS:
                use_lines[sub.id].add(getattr(node, "lineno", fn.lineno))

    pairs: list[tuple[str, int, int]] = []
    for var in TARGET_VARS:
        for d in sorted(def_lines[var]):
            for u in sorted(use_lines[var]):
                if u > d:
                    pairs.append((var, d, u))
    if not pairs:
        raise ValueError("No DU pairs identified for target variables.")
    return pairs


def extract_covered_du_pairs(trace_text: str, source_text: str) -> dict[str, object]:
    all_pairs = _collect_du_pairs(source_text)
    executed_lines: set[int] = set()

    for m in LINE_RE.finditer(trace_text):
        if not m.group("func").endswith(".maybe_promote"):
            continue
        executed_lines.add(int(m.group("lineno")))

    covered = [
        {"var": var, "def_line": d, "use_line": u}
        for (var, d, u) in all_pairs
        if d in executed_lines and u in executed_lines
    ]
    covered.sort(key=lambda x: (x["var"], x["def_line"], x["use_line"]))

    return {"covered_du_pairs": covered}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/maybe_promote_du_pairs_coverage/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/dtypes.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/maybe_promote_du_pairs_coverage/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_covered_du_pairs(trace_text, source_text)

    qa = {
        "question_kind": "S4_DataFlow",
        "question": (
            "Use `xarray/tests/qa/maybe_promote_du_pairs_coverage_test.py`, class "
            "`TestMaybePromoteDUPairsCoverageHardQA`, method "
            "`test_maybe_promote_du_pairs_coverage_case`. During this test execution, inspect "
            "`xarray/core/dtypes.py::maybe_promote`. Considering only variables `dtype_` and "
            "`fill_value`, what are ALL def-use pairs covered by this test? Report each covered pair "
            "as `(var, def_line, use_line)`."
        ),
        "template_answer": {
            "covered_du_pairs": [
                {"var": "str", "def_line": "int", "use_line": "int"}
            ]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
