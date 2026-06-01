#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

TARGET_FILE = Path("/testbed/control/freqplot.py")
TARGET_FUNC_QUAL = "control.freqplot._default_frequency_range"
TARGET_FUNC_NAME = "_default_frequency_range"
TRACKED_VARS = {
    "Hz",
    "features",
    "features_",
    "fn",
    "freq_interesting",
    "lsp_max",
    "lsp_min",
    "omega",
    "sys",
    "syslist",
    "toreplace",
}

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/control/freqplot.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) ",
    re.MULTILINE,
)


class DefUseVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.defs: dict[int, set[str]] = defaultdict(set)
        self.uses: dict[int, set[str]] = defaultdict(set)

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, ast.Store):
            self.defs[node.lineno].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.uses[node.lineno].add(node.id)
        elif isinstance(node.ctx, ast.Del):
            self.defs[node.lineno].add(node.id)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:  # noqa: N802
        if isinstance(node.target, ast.Name):
            self.uses[node.lineno].add(node.target.id)
            self.defs[node.lineno].add(node.target.id)
        else:
            self.visit(node.target)
        self.visit(node.value)


def get_target_function_node(module: ast.Module) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == TARGET_FUNC_NAME:
            return node
    raise ValueError("Could not find target function node.")


def build_def_use_maps(file_text: str) -> tuple[dict[int, set[str]], dict[int, set[str]], int]:
    module = ast.parse(file_text)
    func_node = get_target_function_node(module)

    visitor = DefUseVisitor()
    visitor.visit(func_node)

    filtered_defs: dict[int, set[str]] = {}
    filtered_uses: dict[int, set[str]] = {}

    for line, names in visitor.defs.items():
        keep = names & TRACKED_VARS
        if keep:
            filtered_defs[line] = keep

    for line, names in visitor.uses.items():
        keep = names & TRACKED_VARS
        if keep:
            filtered_uses[line] = keep

    return filtered_defs, filtered_uses, func_node.lineno


def extract_observed_pairs(
    trace_text: str,
    defs_by_line: dict[int, set[str]],
    uses_by_line: dict[int, set[str]],
    param_def_line: int,
) -> list[dict[str, int | str]]:
    invocation_pairs: list[set[tuple[str, int, int]]] = []
    pairs: set[tuple[str, int, int]] = set()
    last_def: dict[str, int] = {}
    param_vars = {
        "syslist",
        "Hz",
    }

    for match in TRACE_RE.finditer(trace_text):
        path = match.group("path")
        func = match.group("func")
        event = match.group("event")
        lineno = int(match.group("lineno"))

        if path != str(TARGET_FILE) or func != TARGET_FUNC_QUAL:
            continue

        if event == "call":
            if last_def:
                invocation_pairs.append(pairs)
            pairs = set()
            last_def = {var: param_def_line for var in param_vars}
            continue

        if event in {"return", "exception"}:
            if last_def:
                invocation_pairs.append(pairs)
            pairs = set()
            last_def = {}
            continue

        for var in sorted(uses_by_line.get(lineno, set())):
            if var in last_def:
                pairs.add((var, last_def[var], lineno))

        for var in sorted(defs_by_line.get(lineno, set())):
            last_def[var] = lineno

    if last_def:
        invocation_pairs.append(pairs)

    if not invocation_pairs:
        intersection: set[tuple[str, int, int]] = set()
    else:
        intersection = set.intersection(*invocation_pairs)

    return [
        {"variable": var, "def_line": def_line, "use_line": use_line}
        for var, def_line, use_line in sorted(
            intersection, key=lambda item: (item[0], item[1], item[2]))
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/freqplot_default_frequency_range_def_use_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/freqplot_default_frequency_range_def_use_suite/oracle.json",
    )
    args = parser.parse_args()

    source_text = TARGET_FILE.read_text(encoding="utf-8")
    defs_by_line, uses_by_line, param_def_line = build_def_use_maps(source_text)
    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    observed_pairs = extract_observed_pairs(
        trace_text, defs_by_line, uses_by_line, param_def_line)

    tracked_vars = ", ".join(f"`{name}`" for name in sorted(TRACKED_VARS))
    qa = {
        "question_kind": "M5_DataFlow",
        "question": (
            "Run the full test suite in "
            "`tests/qa/freqplot_default_frequency_range_def_use_suite_test.py` "
            "(all 10 test methods in `TestDefaultFrequencyRangeDefUseQA`, in file order: "
            "`test_case_01`, `test_case_02`, `test_case_03`, `test_case_04`, "
            "`test_case_05`, `test_case_06`, `test_case_07`, `test_case_08`, "
            "`test_case_09`, and `test_case_10`). The tests import the target directly "
            "with `from control.freqplot import _default_frequency_range`. Focus only on "
            "function `control.freqplot._default_frequency_range` in file "
            "`control/freqplot.py`. Track exactly these variable names: "
            f"{tracked_vars}. For each of the 10 test methods, compute the unique "
            "def-use pairs observed during that method's execution of this function, "
            "then return only the pairs that are present in every one of the 10 "
            "per-test sets. A pair is present for a test method if, during that "
            "method's execution, the value assigned to `variable` at `def_line` is "
            "later read at `use_line` before that variable is redefined. Function "
            "parameters count as defined on the function definition line. Return "
            "the answer as "
            "`observed_def_use_pairs`, a list of objects with exactly these keys: "
            "`variable`, `def_line`, `use_line`. Sort the list by `variable` using "
            "Python's default case-sensitive string ordering, where uppercase "
            "letters sort before lowercase letters; then sort by `def_line`, then "
            "`use_line`, all ascending."
        ),
        "template_answer": {
            "observed_def_use_pairs": [
                {
                    "variable": "str",
                    "def_line": "int",
                    "use_line": "int",
                }
            ]
        },
        "oracle_answer": {
            "observed_def_use_pairs": observed_pairs,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
