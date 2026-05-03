from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE = ROOT_DIR / "src/cfnlint/jsonschema/_resolvers_cfn.py"
TARGET_FUNC_QUAL = "cfnlint.jsonschema._resolvers_cfn.find_in_map"
TARGET_FUNC_NAME = "find_in_map"
INSTANCE_ID = "jsonschema_find_in_map_def_use_pairs"
EXCLUDE_VARS: set[str] = set()

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) ",
    re.MULTILINE,
)

def _is_target_resolvers_path(path: str) -> bool:
    p = path.replace("\\", "/")
    return p.endswith("cfnlint/jsonschema/_resolvers_cfn.py")

class DefUseVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.defs: dict[int, set[str]] = defaultdict(set)
        self.uses: dict[int, set[str]] = defaultdict(set)

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
        if isinstance(node, ast.FunctionDef) and node.name == TARGET_FUNC_NAME:
            return node
    raise ValueError("Could not find target function node.")

def build_def_use_maps(file_text: str) -> tuple[dict[int, set[str]], dict[int, set[str]], set[str], int]:
    module = ast.parse(file_text)
    func_node = get_target_function_node(module)

    visitor = DefUseVisitor()
    visitor.visit(func_node)

    param_names = {arg.arg for arg in func_node.args.args}
    param_def_line = func_node.lineno

    all_local_defs = set()
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

    return filtered_defs, filtered_uses, tracked_vars, param_def_line

def extract_observed_pairs(
    trace_text: str,
    defs_by_line: dict[int, set[str]],
    uses_by_line: dict[int, set[str]],
    tracked_vars: set[str],
) -> list[dict[str, int | str]]:
    pairs: set[tuple[str, int, int]] = set()
    last_def: dict[str, int] = {}

    for match in TRACE_RE.finditer(trace_text):
        path = match.group("path")
        func = match.group("func")
        event = match.group("event")
        lineno = int(match.group("lineno"))

        if not _is_target_resolvers_path(path) or func != TARGET_FUNC_QUAL:
            continue

        if event == "call":
            last_def = {}
            continue

        if event in {"return", "exception"}:
            continue

        for var in uses_by_line.get(lineno, set()):
            if var in last_def:
                pairs.add((var, last_def[var], lineno))

        for var in defs_by_line.get(lineno, set()):
            if var in tracked_vars:
                last_def[var] = lineno

    out = [
        {"variable": var, "def_line": def_line, "use_line": use_line}
        for (var, def_line, use_line) in sorted(pairs, key=lambda x: (x[0], x[1], x[2]))
    ]
    return out

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
    defs_by_line, uses_by_line, tracked_vars, _param_def_line = build_def_use_maps(source_text)
    tracked_names_sorted = sorted(tracked_vars)

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    observed_pairs = extract_observed_pairs(
        trace_text, defs_by_line, uses_by_line, tracked_vars
    )

    var_list = ", ".join(f"`{v}`" for v in tracked_names_sorted)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `tests/qa/testcase.py`, class `TestJsonschemaFindInMapDefUsePairsQA`, method "
            "`test_jsonschema_find_in_map_def_use_pairs_case`. "
            "Focus only on function `cfnlint.jsonschema._resolvers_cfn.find_in_map` in file "
            "`src/cfnlint/jsonschema/_resolvers_cfn.py`. "
            f"Track exactly these variable names: {var_list}. "
            "List all unique def-use pairs observed during this test run for this function. "
            "Return the answer as `observed_def_use_pairs`, a list of objects with exactly these "
            "keys: `variable`, `def_line`, `use_line`. "
            "Each pair means the value assigned to `variable` at `def_line` is later read at "
            "`use_line` before being redefined. Sort the list by `variable`, then `def_line`, then "
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
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line", "call", "return", "exception"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestJsonschemaFindInMapDefUsePairsQA::"
                "test_jsonschema_find_in_map_def_use_pairs_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
