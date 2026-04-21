#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def _parse_exec_order(trace_text: str) -> list[int]:
    """Collect line numbers for analyze_payload from trace (line events only).

    Parse line-by-line (do not use ``^`` in a single regex on the whole file without
    ``re.MULTILINE``, or only the first line can match).
    """
    marker = " event=line locals="
    order: list[int] = []
    for raw_line in trace_text.splitlines():
        line = raw_line.strip()
        if marker not in line:
            continue
        pre, _locals = line.split(marker, 1)
        # Drop optional leading timestamp / prefix before absolute path (e.g. "2024-01-01 ... /testbed/...")
        if "/" in pre:
            slash = pre.find("/")
            if slash > 0:
                pre = pre[slash:]
        idx = pre.rfind(" ")
        if idx == -1:
            continue
        rest = pre[:idx]
        func = pre[idx + 1 :]
        if not func.endswith(".analyze_payload"):
            continue
        try:
            path_part, lineno_str = rest.rsplit(":", 1)
        except ValueError:
            continue
        if not lineno_str.isdigit():
            continue
        path = path_part.replace("\\", "/")
        if not path.endswith("yt_dlp/dupairs.py"):
            continue
        order.append(int(lineno_str))
    if not order:
        raise ValueError("No executed line events captured for analyze_payload in yt_dlp/dupairs.py")
    return order


class _DUVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.defs: dict[int, set[str]] = {}
        self.uses: dict[int, set[str]] = {}

    def _add(self, mp: dict[int, set[str]], node: ast.AST, name: str) -> None:
        lineno = getattr(node, "lineno", None)
        if lineno is None:
            return
        mp.setdefault(lineno, set()).add(name)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self._add(self.defs, node, node.id)
        elif isinstance(node.ctx, ast.Load):
            self._add(self.uses, node, node.id)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # x += y uses x and defines x
        if isinstance(node.target, ast.Name):
            self._add(self.uses, node.target, node.target.id)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        # `for i in ...` defines target, uses iter
        self.visit(node.iter)
        self.visit(node.target)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_comprehension(self, node: ast.comprehension) -> None:  # type: ignore[override]
        # target is a def; iter/ifs are uses
        self.visit(node.iter)
        for iff in node.ifs:
            self.visit(iff)
        self.visit(node.target)


def _find_func(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ValueError(f"Could not find function {name!r} in source.")


def extract_du_pairs(trace_text: str, source_text: str) -> dict[str, object]:
    tree = ast.parse(source_text)
    fn = _find_func(tree, "analyze_payload")

    visitor = _DUVisitor()
    visitor.visit(fn)

    executed = _parse_exec_order(trace_text)

    # Initialize parameter definitions at function start lineno
    last_def: dict[str, int] = {}
    fn_start = fn.lineno
    for arg in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
        last_def[arg.arg] = fn_start

    du_pairs: set[tuple[str, int, int]] = set()
    for lineno in executed:
        # record uses before defs on the same line
        for var in sorted(visitor.uses.get(lineno, set())):
            if var in last_def:
                du_pairs.add((var, last_def[var], lineno))
        for var in sorted(visitor.defs.get(lineno, set())):
            last_def[var] = lineno

    out = sorted(du_pairs, key=lambda t: (t[0], t[1], t[2]))
    return {"du_pairs": [[v, d, u] for (v, d, u) in out]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/du_pairs_covered/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/du_pairs_covered/oracle.json",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/dupairs.py",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source).read_text(encoding="utf-8")
    answer = extract_du_pairs(trace_text, source_text)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `test/qa/du_pairs_covered_test.py`, class `TestDUPairsCoveredQA`, "
            "method `test_du_pairs_covered_case`. In `yt_dlp/dupairs.py`, function "
            "`analyze_payload`, compute ALL dynamic def-use pairs covered during this test for "
            "local variables and parameters. A def-use pair is a triple `(var, def_lineno, use_lineno)` "
            "where `def_lineno` is the line that last defined `var` before a later executed line "
            "`use_lineno` used `var` (uses are counted before defs on the same line). Return all "
            "unique pairs as `du_pairs`, sorted lexicographically by `(var, def_lineno, use_lineno)`."
        ),
        "template_answer": {"du_pairs": [["str", "int", "int"]]},
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

