#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

INSTANCE_ID = "timeresp_check_convert_array_def_use_intersection_suite"
TARGET_FILE = Path("/testbed/control/timeresp.py")
TARGET_FUNC_QUAL = "control.timeresp._check_convert_array"
TARGET_FUNC_NAME = "_check_convert_array"
TEST_FILE = "tests/qa/timeresp_check_convert_array_def_use_intersection_suite_test.py"
TEST_CLASS = "TestCheckConvertArrayDefUseIntersectionQA"
TRACKED_VARS = {
    "err_msg",
    "err_msg_start",
    "in_obj",
    "legal_kinds",
    "legal_shape_str",
    "legal_shapes",
    "n_actual",
    "n_legal",
    "out_array",
    "s_actual",
    "s_legal",
    "squeeze",
    "the_val",
    "transpose",
}

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/control/timeresp.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) ",
    re.MULTILINE,
)


class DefUseVisitor(ast.NodeVisitor):
    def __init__(self):
        self.defs: dict[int, set[str]] = defaultdict(set)
        self.uses: dict[int, set[str]] = defaultdict(set)

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, ast.Store):
            self.defs[node.lineno].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.uses[node.lineno].add(node.id)
        self.generic_visit(node)


def get_function_node(module: ast.Module) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == TARGET_FUNC_NAME:
            return node
    raise ValueError("target function not found")


def build_maps() -> tuple[dict[int, set[str]], dict[int, set[str]], int]:
    module = ast.parse(TARGET_FILE.read_text(encoding="utf-8"))
    func = get_function_node(module)
    visitor = DefUseVisitor()
    visitor.visit(func)
    defs = {line: names & TRACKED_VARS for line, names in visitor.defs.items() if names & TRACKED_VARS}
    uses = {line: names & TRACKED_VARS for line, names in visitor.uses.items() if names & TRACKED_VARS}
    return defs, uses, func.lineno


def extract_intersection(trace_text: str, defs_by_line, uses_by_line, param_def_line):
    invocation_pairs: list[set[tuple[str, int, int]]] = []
    pairs: set[tuple[str, int, int]] = set()
    last_def: dict[str, int] = {}
    param_vars = {"in_obj", "legal_shapes", "err_msg_start", "squeeze", "transpose"}

    for match in TRACE_RE.finditer(trace_text):
        if match.group("path") != str(TARGET_FILE) or match.group("func") != TARGET_FUNC_QUAL:
            continue
        event = match.group("event")
        lineno = int(match.group("lineno"))

        if event == "call":
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

    intersection = set.intersection(*invocation_pairs) if invocation_pairs else set()
    return [
        {"variable": var, "def_line": def_line, "use_line": use_line}
        for var, def_line, use_line in sorted(intersection, key=lambda item: (item[0], item[1], item[2]))
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log")
    parser.add_argument("--out", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json")
    args = parser.parse_args()

    defs_by_line, uses_by_line, param_def_line = build_maps()
    observed_pairs = extract_intersection(
        Path(args.trace_log).read_text(encoding="utf-8"),
        defs_by_line,
        uses_by_line,
        param_def_line,
    )
    tracked_vars = ", ".join(f"`{name}`" for name in sorted(TRACKED_VARS))
    tests = ", ".join(f"`test_case_{i:02d}`" for i in range(1, 11))
    qa = {
        "question_kind": "M5_DataFlow",
        "question": (
            f"Run the full test suite in `{TEST_FILE}` (all 10 test methods in "
            f"`{TEST_CLASS}`, in file order: {tests}). The tests import the target "
            "directly with `from control.timeresp import _check_convert_array`. Focus "
            "only on function `control.timeresp._check_convert_array` in file "
            "`control/timeresp.py`. Count only reads and writes that execute directly "
            "in this function's own call frame: variables defined or used inside a "
            "nested/inner function definition, a lambda, or a comprehension scope "
            "(each of which runs in its own separate frame) do not count, even if they "
            "share one of the tracked names. Track exactly these variable names: "
            f"{tracked_vars}. For each of the 10 test methods, compute the unique "
            "def-use pairs observed during that method's execution of this function, "
            "then return only the pairs that are present in every one of the 10 "
            "per-test sets. A pair is present for a test method if, during that "
            "method's execution, the value assigned to `variable` at `def_line` is "
            "later read at `use_line` before that variable is redefined. Function "
            "parameters count as defined on the function definition line. Return the "
            "answer as `observed_def_use_pairs`, a list of objects with exactly these "
            "keys: `variable`, `def_line`, `use_line`. Sort the list by `variable` "
            "using Python's default case-sensitive string ordering, where uppercase "
            "letters sort before lowercase letters; then sort by `def_line`, then "
            "`use_line`, all ascending."
        ),
        "template_answer": {
            "observed_def_use_pairs": [
                {"variable": "str", "def_line": "int", "use_line": "int"}
            ]
        },
        "oracle_answer": {"observed_def_use_pairs": observed_pairs},
    }
    Path(args.out).write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
