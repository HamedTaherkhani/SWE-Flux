#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

TARGET_FILE = Path("/testbed/libqtile/core/manager.py")
TARGET_CLASS_NAME = "Qtile"
TARGET_FUNC_NAME = "process_key_event"
TARGET_FUNCS = {
    "libqtile.core.manager.process_key_event",
    "libqtile.core.manager.Qtile.process_key_event",
}
TRACKED_VARS = {"keysym", "mask", "key", "executed", "cmd", "status", "val"}

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/core/manager\.py):(?P<lineno>\d+) "
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
        if isinstance(node, ast.ClassDef) and node.name == TARGET_CLASS_NAME:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == TARGET_FUNC_NAME:
                    return child
    raise ValueError("Could not find target function node.")


def build_def_use_maps(file_text: str):
    module = ast.parse(file_text)
    func_node = get_target_function_node(module)

    visitor = DefUseVisitor()
    visitor.visit(func_node)

    param_names = {arg.arg for arg in func_node.args.args}
    param_def_line = func_node.lineno

    filtered_defs = {}
    filtered_uses = {}

    for line, names in visitor.defs.items():
        keep = {n for n in names if n in TRACKED_VARS}
        if keep:
            filtered_defs[line] = keep

    for line, names in visitor.uses.items():
        keep = {n for n in names if n in TRACKED_VARS}
        if keep:
            filtered_uses[line] = keep

    return filtered_defs, filtered_uses, param_names, param_def_line


def extract_observed_pairs(
    trace_text: str,
    defs_by_line: dict[int, set[str]],
    uses_by_line: dict[int, set[str]],
    param_names: set[str],
    param_def_line: int,
) -> list[dict[str, int | str]]:
    pairs: set[tuple[str, int, int]] = set()
    frame_stack: list[dict[str, int]] = []

    for match in TRACE_RE.finditer(trace_text):
        func = match.group("func")
        event = match.group("event")
        lineno = int(match.group("lineno"))

        if func not in TARGET_FUNCS:
            continue

        if event == "call":
            frame_stack.append({v: param_def_line for v in TRACKED_VARS if v in param_names})
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
        {"variable": var, "def_line": dline, "use_line": uline}
        for (var, dline, uline) in sorted(pairs, key=lambda x: (x[0], x[1], x[2]))
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_direct_process_key_event_def_use_pairs/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_direct_process_key_event_def_use_pairs/oracle.json"
        ),
    )
    args = parser.parse_args()

    source_text = TARGET_FILE.read_text(encoding="utf-8")
    defs_by_line, uses_by_line, param_names, param_def_line = build_def_use_maps(source_text)

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    observed_pairs = extract_observed_pairs(
        trace_text, defs_by_line, uses_by_line, param_names, param_def_line
    )

    qa = {
        "question_kind": "S4_DataFlow",
        "question": (
            "Use `tests/qa/core_manager_direct_process_key_event_def_use_pairs_test.py`, class "
            "`TestCoreManagerDirectProcessKeyEventDefUsePairsQA`, method "
            "`test_core_manager_direct_process_key_event_def_use_pairs_case`. "
            "Focus only on function `libqtile.core.manager.process_key_event` in file "
            "`libqtile/core/manager.py`. "
            "Track exactly these variable names: `keysym`, `mask`, `key`, `executed`, `cmd`, `status`, `val`. "
            "List all unique def-use pairs observed during this test run for this function. "
            "Return the answer as `observed_def_use_pairs`, a list of objects with exactly these keys: "
            "`variable`, `def_line`, `use_line`. "
            "Each pair means the value assigned to `variable` at `def_line` is later read at `use_line` "
            "before being redefined. Sort the list by `variable`, then `def_line`, then `use_line`, all ascending."
        ),
        "template_answer": {
            "observed_def_use_pairs": [
                {"variable": "str", "def_line": "int", "use_line": "int"}
            ]
        },
        "oracle_answer": {"observed_def_use_pairs": observed_pairs},
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
