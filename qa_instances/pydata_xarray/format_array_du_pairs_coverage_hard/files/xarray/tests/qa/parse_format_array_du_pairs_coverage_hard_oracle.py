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
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)

TARGET_VARS = {"count", "num_front", "num_back", "pprint_str", "padding", "max_len"}


class DefUseCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.defs_by_line: dict[int, set[str]] = {}
        self.uses_by_line: dict[int, set[str]] = {}

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in TARGET_VARS:
            if isinstance(node.ctx, ast.Store):
                self.defs_by_line.setdefault(node.lineno, set()).add(node.id)
            elif isinstance(node.ctx, ast.Load):
                self.uses_by_line.setdefault(node.lineno, set()).add(node.id)
        self.generic_visit(node)


def _extract_function(source_text: str, func_name: str) -> ast.FunctionDef:
    mod = ast.parse(source_text)
    for node in mod.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return node
    raise ValueError(f"Function {func_name!r} not found.")


def _arg_names(func: ast.FunctionDef) -> set[str]:
    names = {a.arg for a in func.args.args}
    names.update(a.arg for a in getattr(func.args, "posonlyargs", []))
    names.update(a.arg for a in func.args.kwonlyargs)
    if func.args.vararg:
        names.add(func.args.vararg.arg)
    if func.args.kwarg:
        names.add(func.args.kwarg.arg)
    return names


def extract_pairs(trace_text: str, source_text: str) -> dict[str, list[dict[str, int | str]]]:
    func_node = _extract_function(source_text, "format_array_flat")
    collector = DefUseCollector()
    collector.visit(func_node)

    executed_lines: list[int] = []
    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if func.endswith(".format_array_flat"):
            executed_lines.append(int(m.group("lineno")))

    if not executed_lines:
        raise ValueError("Could not find format_array_flat line events in trace.")

    latest_def: dict[str, int] = {}
    for arg in _arg_names(func_node):
        if arg in TARGET_VARS:
            latest_def[arg] = func_node.lineno

    pairs: list[dict[str, int | str]] = []
    seen = set()

    for line in executed_lines:
        for var in sorted(collector.uses_by_line.get(line, set())):
            if var in latest_def:
                key = (var, latest_def[var], line)
                if key not in seen:
                    seen.add(key)
                    pairs.append({"var": var, "def_line": latest_def[var], "use_line": line})

        for var in sorted(collector.defs_by_line.get(line, set())):
            latest_def[var] = line

    if not pairs:
        raise ValueError("No def-use pairs found for target variables.")

    return {"covered_def_use_pairs": pairs}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/format_array_du_pairs_coverage_hard/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/formatting.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/format_array_du_pairs_coverage_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_pairs(trace_text, source_text)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `xarray/tests/qa/format_array_du_pairs_coverage_hard_test.py`, class "
            "`TestFormatArrayDUPairsCoverageHardQA`, method "
            "`test_format_array_du_pairs_coverage_hard_case`. "
            "This test calls `xarray/core/formatting.py::format_array_flat` three times (lines 12-14). "
            "Within `format_array_flat`, consider only variables "
            "`count`, `num_front`, `num_back`, `pprint_str`, `padding`, and `max_len`. "
            "Across the full test execution, what are ALL covered def-use pairs for those variables, "
            "reported as objects with keys `var`, `def_line`, and `use_line`?"
        ),
        "template_answer": {
            "covered_def_use_pairs": [{"var": "str", "def_line": "int", "use_line": "int"}]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
