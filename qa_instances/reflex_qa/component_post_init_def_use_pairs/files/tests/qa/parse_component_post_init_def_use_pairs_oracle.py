#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

TARGET_FILE = Path("/testbed/reflex/components/component.py")
TARGET_FUNC_QUAL = "reflex.components.component.Component._post_init"
TARGET_FUNC_NAME = "_post_init"
TARGET_FUNC_LINE = 461
TRACKED_VARS = {
    "self",
    "args",
    "kwargs",
    "children",
    "fields",
    "component_specific_triggers",
    "props",
    "key",
    "value",
    "is_var",
    "field",
    "expected_type",
    "passed_type",
    "value_name",
    "additional_info",
    "special_attributes",
    "custom_attrs",
    "style",
    "style_dict",
    "fields_style",
    "class_name",
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
    for node in ast.walk(module):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == TARGET_FUNC_NAME
            and node.lineno == TARGET_FUNC_LINE
        ):
            return node
    raise ValueError("Could not find target function node.")


def build_def_use_maps(file_text: str) -> tuple[dict[int, set[str]], dict[int, set[str]], int]:
    module = ast.parse(file_text)
    func_node = get_target_function_node(module)
    visitor = DefUseVisitor()
    visitor.visit(func_node)
    defs_by_line = {
        line: names & TRACKED_VARS
        for line, names in visitor.defs.items()
        if names & TRACKED_VARS
    }
    uses_by_line = {
        line: names & TRACKED_VARS
        for line, names in visitor.uses.items()
        if names & TRACKED_VARS
    }
    return defs_by_line, uses_by_line, func_node.lineno


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
            frame_stack.append({"self": param_def_line, "args": param_def_line, "kwargs": param_def_line})
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
        for var, def_line, use_line in sorted(pairs, key=lambda x: (x[0], x[1], x[2]))
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default="/testbed/logs/qa_instances/component_post_init_def_use_pairs/trace.log")
    parser.add_argument("--out", default="/testbed/logs/qa_instances/component_post_init_def_use_pairs/oracle.json")
    args = parser.parse_args()

    defs_by_line, uses_by_line, param_def_line = build_def_use_maps(TARGET_FILE.read_text(encoding="utf-8"))
    observed_pairs = extract_observed_pairs(Path(args.trace_log).read_text(encoding="utf-8"), defs_by_line, uses_by_line, param_def_line)
    qa = {
        "question_kind": "S4_DataFlow",
        "question": (
            "Use `tests/qa/component_post_init_def_use_pairs_test.py`, class "
            "`TestComponentPostInitDefUsePairsQA`, method "
            "`test_component_post_init_def_use_pairs_case`. The test constructs a Radix "
            "`Box` by calling `Box.create(...)` at lines 9-24 with a nested `rx.text(...)` "
            "child at lines 10-14, list-valued `class_name`, a two-entry style list, "
            "`data_state`, `aria_label`, and `on_click`. Focus only on method "
            "`reflex.components.component.Component._post_init` in file "
            "`reflex/components/component.py`, lines 461-623. Track exactly these variable "
            "names from that method: `self`, `args`, `kwargs`, `children`, `fields`, "
            "`component_specific_triggers`, `props`, `key`, `value`, `is_var`, `field`, "
            "`expected_type`, `passed_type`, `value_name`, `additional_info`, "
            "`special_attributes`, `custom_attrs`, `style`, `style_dict`, `fields_style`, "
            "`class_name`. List all unique def-use pairs observed during this test run for "
            "this method. Return the answer as `observed_def_use_pairs`, a list of objects "
            "with exactly these keys: `variable`, `def_line`, `use_line`. Each pair means "
            "the value assigned to `variable` at `def_line` is later read at `use_line` "
            "before being redefined in the same active call frame. Sort the list by "
            "`variable`, then `def_line`, then `use_line`, all ascending."
        ),
        "template_answer": {"observed_def_use_pairs": [{"variable": "str", "def_line": "int", "use_line": "int"}]},
        "oracle_answer": {"observed_def_use_pairs": observed_pairs},
    }
    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
