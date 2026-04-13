#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def _parse_exec_order(trace_text: str) -> list[int]:
    marker = " event=line locals="
    order: list[int] = []
    for raw_line in trace_text.splitlines():
        line = raw_line.strip()
        if marker not in line:
            continue
        pre, _locals = line.split(marker, 1)
        if "/" in pre:
            slash = pre.find("/")
            if slash > 0:
                pre = pre[slash:]
        idx = pre.rfind(" ")
        if idx == -1:
            continue
        rest = pre[:idx]
        func = pre[idx + 1 :]
        if not func.endswith(".fold_scalar"):
            continue
        try:
            path_part, lineno_str = rest.rsplit(":", 1)
        except ValueError:
            continue
        if not lineno_str.isdigit():
            continue
        path = path_part.replace("\\", "/")
        if not path.endswith("yt_dlp/wisp_trace.py"):
            continue
        order.append(int(lineno_str))
    if not order:
        raise ValueError("No line events for fold_scalar in yt_dlp/wisp_trace.py")
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
        if isinstance(node.target, ast.Name):
            self._add(self.uses, node.target, node.target.id)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self.visit(node.target)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_comprehension(self, node: ast.comprehension) -> None:  # type: ignore[override]
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
    fn = _find_func(tree, "fold_scalar")

    visitor = _DUVisitor()
    visitor.visit(fn)

    executed = _parse_exec_order(trace_text)

    last_def: dict[str, int] = {}
    fn_start = fn.lineno
    for arg in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
        last_def[arg.arg] = fn_start

    du_pairs: set[tuple[str, int, int]] = set()
    for lineno in executed:
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
        default="/testbed/logs/qa_instances/wisp_du_pairs_probe/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/wisp_du_pairs_probe/oracle.json",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/wisp_trace.py",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source).read_text(encoding="utf-8")
    answer = extract_du_pairs(trace_text, source_text)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `test/qa/wisp_du_pairs_probe_test.py`, class `TestWispDuPairsProbeQA`, method "
            "`test_wisp_du_pairs_probe_case`. In `yt_dlp/wisp_trace.py`, function `fold_scalar`, compute ALL "
            "dynamic def-use pairs covered during this single test for local variables and parameters. A def-use "
            "pair is a triple `(var, def_lineno, use_lineno)` where `def_lineno` is the source line that last "
            "defined `var` before a later executed line `use_lineno` where `var` is read (uses before defs on the "
            "same line). Parameters are considered defined on the `def fold_scalar` line. Return every distinct "
            "pair as `du_pairs`, sorted lexicographically by `(var, def_lineno, use_lineno)`."
        ),
        "template_answer": {"du_pairs": [["str", "int", "int"]]},
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
