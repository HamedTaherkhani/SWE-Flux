#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

INSTANCE_ID = "statesp_convert_to_statespace_def_use_intersection_suite"
TARGET_FILE = Path("/testbed/control/statesp.py")
TARGET_FUNC_QUAL = "control.statesp._convert_to_statespace"
TARGET_FUNC_NAME = "_convert_to_statespace"
TEST_FILE = "tests/qa/statesp_convert_to_statespace_def_use_intersection_suite_test.py"
TEST_CLASS = "TestConvertToStateSpaceDefUseIntersectionQA"
TRACKED_VARS = {
    "A",
    "B",
    "C",
    "D",
    "d",
    "drow",
    "maxd",
    "maxn",
    "method",
    "newsys",
    "n",
    "nrow",
    "sys",
    "use_prefix_suffix",
}

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/control/statesp.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) (?P<rest>.*)$",
    re.MULTILINE,
)

_LOCALS_RE = re.compile(r"locals=(\{.*\})\s*$")


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


class _Unevaluable(Exception):
    """Raised when an expression cannot be evaluated from reconstructed locals."""


_UNKNOWN = object()


class GuardedUseCollector(ast.NodeVisitor):
    """Collect tracked-variable reads together with the boolean short-circuit
    guards that must hold for the read to actually execute.

    For each ``Load`` of a tracked variable we record ``(lineno, var, guard)``
    where ``guard`` is the tuple of ``(operand_node, is_and)`` for every
    preceding operand of every enclosing ``and``/``or``. The read executes only
    if each preceding ``and`` operand was truthy and each preceding ``or``
    operand was falsy.
    """

    def __init__(self, tracked: set[str]):
        self.tracked = tracked
        self.by_line: dict[int, list[tuple[str, tuple]]] = defaultdict(list)
        self._stack: list[tuple[ast.AST, bool]] = []

    def visit_BoolOp(self, node: ast.BoolOp) -> None:  # noqa: N802
        is_and = isinstance(node.op, ast.And)
        for i, value in enumerate(node.values):
            pushed = [(node.values[j], is_and) for j in range(i)]
            self._stack.extend(pushed)
            self.visit(value)
            if pushed:
                del self._stack[-len(pushed):]

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, ast.Load) and node.id in self.tracked:
            self.by_line[node.lineno].append((node.id, tuple(self._stack)))


def get_function_node(module: ast.Module) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == TARGET_FUNC_NAME:
            return node
    raise ValueError("target function not found")


def build_maps():
    module = ast.parse(TARGET_FILE.read_text(encoding="utf-8"))
    func = get_function_node(module)
    visitor = DefUseVisitor()
    visitor.visit(func)
    defs = {line: names & TRACKED_VARS for line, names in visitor.defs.items() if names & TRACKED_VARS}
    collector = GuardedUseCollector(TRACKED_VARS)
    collector.visit(func)
    use_occurrences = dict(collector.by_line)
    return defs, use_occurrences, func.lineno


def _truthy(value) -> bool:
    return bool(value)


def _apply_cmp(op: ast.cmpop, left, right) -> bool:
    if isinstance(op, ast.Eq):
        return left == right
    if isinstance(op, ast.NotEq):
        return left != right
    if isinstance(op, ast.Lt):
        return left < right
    if isinstance(op, ast.LtE):
        return left <= right
    if isinstance(op, ast.Gt):
        return left > right
    if isinstance(op, ast.GtE):
        return left >= right
    if isinstance(op, ast.Is):
        return left is right
    if isinstance(op, ast.IsNot):
        return left is not right
    if isinstance(op, ast.In):
        return left in right
    if isinstance(op, ast.NotIn):
        return left not in right
    raise _Unevaluable


def _safe_eval(node: ast.AST, env: dict):
    """Best-effort evaluation of a pure expression from reconstructed locals.

    Only constants, known locals, comparisons, ``not`` and ``and``/``or`` are
    supported; anything else (calls, attributes, unknown names, …) raises
    ``_Unevaluable`` so the caller can fall back to a conservative decision.
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        value = env.get(node.id, _UNKNOWN)
        if value is _UNKNOWN:
            raise _Unevaluable
        return value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _truthy(_safe_eval(node.operand, env))
    if isinstance(node, ast.BoolOp):
        is_and = isinstance(node.op, ast.And)
        last = None
        for value in node.values:
            last = _safe_eval(value, env)
            if is_and and not _truthy(last):
                return last
            if not is_and and _truthy(last):
                return last
        return last
    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left, env)
        for op, comparator in zip(node.ops, node.comparators):
            right = _safe_eval(comparator, env)
            if not _apply_cmp(op, left, right):
                return False
            left = right
        return True
    raise _Unevaluable


def _reached(guard: tuple, env: dict) -> bool:
    """Whether a use behind ``guard`` actually executed.

    Returns ``False`` only when some preceding operand is *provably* blocking
    (short-circuit determined from reconstructed locals); indeterminate
    operands are assumed evaluated so a real read is never dropped.
    """
    for operand_node, is_and in guard:
        try:
            value = _truthy(_safe_eval(operand_node, env))
        except _Unevaluable:
            continue
        if is_and and not value:
            return False
        if not is_and and value:
            return False
    return True


def _parse_locals_delta(rest: str) -> dict:
    match = _LOCALS_RE.search(rest)
    if not match:
        return {}
    try:
        raw = ast.literal_eval(match.group(1))
    except Exception:
        return {}
    delta = {}
    for name, repr_value in raw.items():
        if isinstance(repr_value, str):
            try:
                delta[name] = ast.literal_eval(repr_value)
            except Exception:
                delta[name] = _UNKNOWN
        else:
            delta[name] = repr_value
    return delta


def extract_intersection(trace_text: str, defs_by_line, use_occurrences, param_def_line):
    invocation_pairs: list[set[tuple[str, int, int]]] = []
    pairs: set[tuple[str, int, int]] = set()
    last_def: dict[str, int] = {}
    cur_locals: dict = {}
    param_vars = {"sys", "use_prefix_suffix", "method"}

    for match in TRACE_RE.finditer(trace_text):
        if match.group("path") != str(TARGET_FILE) or match.group("func") != TARGET_FUNC_QUAL:
            continue
        event = match.group("event")
        lineno = int(match.group("lineno"))
        if event == "call":
            pairs = set()
            last_def = {var: param_def_line for var in param_vars}
            cur_locals = {}
            continue
        if event in {"return", "exception"}:
            if last_def:
                invocation_pairs.append(pairs)
            pairs = set()
            last_def = {}
            cur_locals = {}
            continue
        cur_locals.update(_parse_locals_delta(match.group("rest")))
        used_vars = {
            var
            for var, guard in use_occurrences.get(lineno, [])
            if _reached(guard, cur_locals)
        }
        for var in sorted(used_vars):
            if var in last_def:
                pairs.add((var, last_def[var], lineno))
        for var in sorted(defs_by_line.get(lineno, set())):
            last_def[var] = lineno

    intersection = set.intersection(*invocation_pairs) if invocation_pairs else set()
    return [
        {"variable": var, "def_line": def_line, "use_line": use_line}
        for var, def_line, use_line in sorted(intersection, key=lambda item: (item[0], item[1], item[2]))
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log")
    parser.add_argument("--out", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json")
    args = parser.parse_args()
    defs_by_line, uses_by_line, param_def_line = build_maps()
    observed_pairs = extract_intersection(
        Path(args.trace_log).read_text(encoding="utf-8"), defs_by_line, uses_by_line, param_def_line)
    tracked_vars = ", ".join(f"`{name}`" for name in sorted(TRACKED_VARS))
    tests = ", ".join(f"`test_case_{i:02d}`" for i in range(1, 11))
    qa = {
        "question_kind": "M4_DataFlow",
        "question": (
            f"Run the full test suite in `{TEST_FILE}` (all 10 test methods in "
            f"`{TEST_CLASS}`, in file order: {tests}). The tests import the target "
            "directly with `from control.statesp import _convert_to_statespace`. "
            "Focus only on function `control.statesp._convert_to_statespace` in file "
            f"`control/statesp.py`. Track exactly these variable names: {tracked_vars}. "
            "For each of the 10 test methods, compute the unique def-use pairs observed "
            "during that method's execution of this function, then return only the pairs "
            "that are present in every one of the 10 per-test sets. A pair is present "
            "for a test method if, during that method's execution, the value assigned "
            "to `variable` at `def_line` is later read at `use_line` before that "
            "variable is redefined. Function parameters count as defined on the "
            "function definition line. Return the answer as `observed_def_use_pairs`, "
            "a list of objects with exactly these keys: `variable`, `def_line`, "
            "`use_line`. Sort the list by `variable` using Python's default "
            "case-sensitive string ordering, where uppercase letters sort before "
            "lowercase letters; then sort by `def_line`, then `use_line`, all ascending."
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
