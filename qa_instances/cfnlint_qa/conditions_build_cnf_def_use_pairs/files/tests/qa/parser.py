from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE = ROOT_DIR / "src/cfnlint/conditions/conditions.py"
TARGET_FUNC_QUAL = "cfnlint.conditions.conditions.Conditions._build_cnf"
TARGET_CLASS_NAME = "Conditions"
TARGET_FUNC_NAME = "_build_cnf"
INSTANCE_ID = "conditions_build_cnf_def_use_pairs"
EXCLUDE_VARS: set[str] = {"self", "_"}

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) ",
    re.MULTILINE,
)

def _is_target_path(path: str) -> bool:
    return path.replace("\\", "/").endswith("cfnlint/conditions/conditions.py")

class DefUseVisitor(ast.NodeVisitor):

    def __init__(self) -> None:
        self.defs: dict[int, set[str]] = defaultdict(set)
        self.uses: dict[int, set[str]] = defaultdict(set)

    def visit_FunctionDef(self, node):
        return

    def visit_AsyncFunctionDef(self, node):
        return

    def visit_Lambda(self, node):
        return

    def visit_Name(self, node: ast.Name) -> None:
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
                if (
                    isinstance(child, ast.FunctionDef)
                    and child.name == TARGET_FUNC_NAME
                ):
                    return child
    raise ValueError("Could not find target function node.")

def build_def_use_maps(
    file_text: str,
) -> tuple[dict[int, set[str]], dict[int, set[str]], set[str]]:
    module = ast.parse(file_text)
    func_node = get_target_function_node(module)

    visitor = DefUseVisitor()
    for stmt in func_node.body:
        visitor.visit(stmt)

    param_names = {arg.arg for arg in func_node.args.args}

    all_local_defs: set[str] = set()
    for names in visitor.defs.values():
        all_local_defs.update(names)

    tracked_vars = (all_local_defs | param_names) - EXCLUDE_VARS

    filtered_defs: dict[int, set[str]] = {}
    filtered_uses: dict[int, set[str]] = {}

    for line, names in visitor.defs.items():
        keep = {n for n in names if n in tracked_vars and n not in EXCLUDE_VARS}
        if keep:
            filtered_defs[line] = keep
    for line, names in visitor.uses.items():
        keep = {n for n in names if n in tracked_vars and n not in EXCLUDE_VARS}
        if keep:
            filtered_uses[line] = keep

    return filtered_defs, filtered_uses, tracked_vars

def extract_observed_pairs(
    trace_text: str,
    defs_by_line: dict[int, set[str]],
    uses_by_line: dict[int, set[str]],
    tracked_vars: set[str],
) -> list[dict[str, object]]:
    pairs: set[tuple[str, int, int]] = set()
    last_def_stack: list[dict[str, int]] = []

    for match in TRACE_RE.finditer(trace_text):
        path = match.group("path")
        func = match.group("func")
        event = match.group("event")
        lineno = int(match.group("lineno"))

        if not _is_target_path(path) or func != TARGET_FUNC_QUAL:
            continue

        if event == "call":
            last_def_stack.append({})
            continue
        if event == "return":
            if last_def_stack:
                last_def_stack.pop()
            continue
        if event == "exception":
            continue
        if event != "line" or not last_def_stack:
            continue

        current = last_def_stack[-1]
        for var in uses_by_line.get(lineno, set()):
            if var in current:
                pairs.add((var, current[var], lineno))
        for var in defs_by_line.get(lineno, set()):
            if var in tracked_vars:
                current[var] = lineno

    return [
        {"variable": var, "def_line": d, "use_line": u}
        for (var, d, u) in sorted(pairs, key=lambda x: (x[0], x[1], x[2]))
    ]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log",
    )
    parser.add_argument(
        "--out",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json",
    )
    args = parser.parse_args()

    source_text = TARGET_FILE.read_text(encoding="utf-8")
    defs_by_line, uses_by_line, tracked_vars = build_def_use_maps(source_text)
    tracked_names_sorted = sorted(tracked_vars)

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    observed_pairs = extract_observed_pairs(
        trace_text, defs_by_line, uses_by_line, tracked_vars
    )

    var_list = ", ".join(f"`{v}`" for v in tracked_names_sorted)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestConditionsBuildCnfDefUsePairsQA`, method "
            "`test_conditions_build_cnf_def_use_pairs_case`. Focus only on method "
            "`cfnlint.conditions.conditions.Conditions._build_cnf` in file "
            "`src/cfnlint/conditions/conditions.py`. The method has FIVE phases: "
            "(1) initialise `cnf`, `equal_vars`, `equals`; (2) define and drive "
            "the nested closure `_build_equal_vars` over `self._rules` and the "
            "`condition_names` argument; (3) AllowedValues cleanup loop "
            "`for _, equal_1 in equals.items()` (lines 153-166), inner loop "
            "`for param in equal_1.parameters`; (4) NAND-prop emission "
            "`for allowed_hash, allowed_value in allowed_values.items()` (lines "
            "170-187), inner loops binding `equal_1`, `param`, and `prop`; "
            "(5) per-rule `cnf.add_prop(rule.build_cnf(equal_vars))` (lines "
            f"189-190). Track exactly these variable names: {var_list}. Do NOT "
            "track variables defined inside the nested closure "
            "`_build_equal_vars` -- it is a separate scope. List all unique "
            "def-use pairs observed during this test run for this method, "
            "aggregating across every call. Return the answer as "
            "`observed_def_use_pairs`, a list of objects with exactly these "
            "keys: `variable`, `def_line`, `use_line`. Each pair means the "
            "value assigned to `variable` at `def_line` is later read at "
            "`use_line` before being redefined within the SAME call frame. "
            "Sort the list by `variable`, then `def_line`, then `use_line`, "
            "all ascending."
        ),
        "template_answer": {
            "observed_def_use_pairs": [
                {"variable": "str", "def_line": "int", "use_line": "int"}
            ]
        },
        "oracle_answer": {
            "observed_def_use_pairs": observed_pairs,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line", "call", "return", "exception"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestConditionsBuildCnfDefUsePairsQA::"
                "test_conditions_build_cnf_def_use_pairs_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
