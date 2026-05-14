#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

TARGET_FILE = Path("/testbed/reflex/style.py")
TARGET_FUNC_QUAL = "reflex.style.convert"
TARGET_FUNC_NAME = "convert"
TRACKED_VARS = {
    "style_dict",
    "var_data",
    "out",
    "key",
    "value",
    "keys",
    "return_val",
    "new_var_data",
}

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/reflex/[^:]+):(?P<lineno>\d+) "
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
    pairs: set[tuple[str, int, int]] = set()
    frame_stack: list[dict[str, int]] = []

    for match in TRACE_RE.finditer(trace_text):
        path = match.group("path")
        func = match.group("func")
        event = match.group("event")
        lineno = int(match.group("lineno"))

        if path != str(TARGET_FILE) or func != TARGET_FUNC_QUAL:
            continue

        if event == "call":
            frame_stack.append({"style_dict": param_def_line})
            continue

        if not frame_stack:
            continue

        if event in {"return", "exception"}:
            frame_stack.pop()
            continue

        last_def = frame_stack[-1]

        for var in uses_by_line.get(lineno, set()):
            if var in last_def:
                pairs.add((var, last_def[var], lineno))

        for var in defs_by_line.get(lineno, set()):
            last_def[var] = lineno

    return [
        {"variable": var, "def_line": def_line, "use_line": use_line}
        for (var, def_line, use_line) in sorted(pairs, key=lambda x: (x[0], x[1], x[2]))
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/style_convert_def_use_pairs/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/style_convert_def_use_pairs/oracle.json",
    )
    args = parser.parse_args()

    source_text = TARGET_FILE.read_text(encoding="utf-8")
    defs_by_line, uses_by_line, param_def_line = build_def_use_maps(source_text)

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    observed_pairs = extract_observed_pairs(
        trace_text, defs_by_line, uses_by_line, param_def_line
    )

    qa = {
        "question_kind": "C5_DataFlow",
        "question": (
            "Use `tests/qa/style_convert_def_use_pairs_test.py`, class "
            "`TestStyleConvertDefUsePairsQA`, method `test_style_convert_def_use_pairs_case`. "
            "The `raw_style` value is constructed at lines 9-22, and line 24 calls "
            "`convert(raw_style)`. Focus only on function `reflex.style.convert` in file "
            "`reflex/style.py`, lines 161-218. Track exactly these variable names from that "
            "function: `style_dict`, `var_data`, `out`, `key`, `value`, `keys`, "
            "`return_val`, `new_var_data`. List all unique def-use pairs observed during "
            "this test run for this function. Return the answer as `observed_def_use_pairs`, "
            "a list of objects with exactly these keys: `variable`, `def_line`, `use_line`. "
            "Each pair means the value assigned to `variable` at `def_line` is later read at "
            "`use_line` before being redefined in the same active call frame. Sort the list "
            "by `variable`, then `def_line`, then `use_line`, all ascending."
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
