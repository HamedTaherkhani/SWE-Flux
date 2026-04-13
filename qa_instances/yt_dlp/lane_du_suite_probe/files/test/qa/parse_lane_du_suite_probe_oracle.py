#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path


def _normalize_trace_line(raw: str) -> str:
    s = raw.strip()
    if len(s) > 19 and s[4] == "-" and s[7] == "-" and "/" in s:
        slash = s.find("/")
        if slash != -1:
            s = s[slash:]
    return s


EVENT_RE = re.compile(
    r"^(?P<path>[^:]+):(?P<lineno>\d+) (?P<func>\S+) event=(?P<ev>call|line|return)\b"
)

TARGET_SUFFIX = "yt_dlp/bind_lane.py"
CANONICAL_INPUTS: list[tuple[int, str]] = [
    (0, ""),
    (1, "x"),
    (2, "x"),
    (0, "ab"),
    (1, "ab"),
]


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


def _dynamic_pairs_for_order(
    visitor: _DUVisitor,
    fn: ast.FunctionDef,
    executed: list[int],
) -> set[tuple[str, int, int]]:
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
    return du_pairs


def _trace_tube_digest_line_order(tube_digest, seed: int, label: str) -> list[int]:
    lines: list[int] = []

    def tracer(frame, event, arg):  # type: ignore[no-untyped-def]
        if event != "line":
            return tracer
        if frame.f_code.co_name != "tube_digest":
            return tracer
        lines.append(frame.f_lineno)
        return tracer

    sys.settrace(tracer)
    try:
        tube_digest(seed, label)
    finally:
        sys.settrace(None)
    return lines


def _import_tube_digest(source_path: Path):
    root = source_path.resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from yt_dlp.bind_lane import tube_digest  # noqa: PLC0415

    return tube_digest


def _parse_tube_digest_orders(trace_text: str) -> list[list[int]]:
    orders: list[list[int]] = []
    cur: list[int] | None = None
    for raw in trace_text.splitlines():
        s = _normalize_trace_line(raw)
        m = EVENT_RE.match(s)
        if not m:
            continue
        path = m.group("path").replace("\\", "/")
        if not path.endswith(TARGET_SUFFIX):
            continue
        func = m.group("func")
        if func != "yt_dlp.bind_lane.tube_digest" and not func.endswith(".tube_digest"):
            continue
        ev = m.group("ev")
        lineno = int(m.group("lineno"))
        if ev == "call":
            cur = []
        elif ev == "line":
            if cur is not None:
                cur.append(lineno)
        elif ev == "return":
            if cur is not None:
                orders.append(cur)
            cur = None

    if not orders:
        raise ValueError(
            "No call/line/return sequences captured for yt_dlp.bind_lane.tube_digest in trace log."
        )
    return orders


def extract_du_suite_coverage(
    trace_text: str,
    source_text: str,
    source_path: Path,
) -> dict[str, object]:
    tree = ast.parse(source_text)
    fn = _find_func(tree, "tube_digest")
    visitor = _DUVisitor()
    visitor.visit(fn)

    tube_digest = _import_tube_digest(source_path)

    required: set[tuple[str, int, int]] = set()
    for seed, label in CANONICAL_INPUTS:
        order = _trace_tube_digest_line_order(tube_digest, seed, label)
        required |= _dynamic_pairs_for_order(visitor, fn, order)

    observed: set[tuple[str, int, int]] = set()
    for order in _parse_tube_digest_orders(trace_text):
        observed |= _dynamic_pairs_for_order(visitor, fn, order)

    missing = sorted(required - observed, key=lambda t: (t[0], t[1], t[2]))
    all_covered = not missing

    return {
        "all_du_pairs_covered": all_covered,
        "missing_du_pairs": [[v, d, u] for (v, d, u) in missing],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/lane_du_suite_probe/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/lane_du_suite_probe/oracle.json",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/bind_lane.py",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = source_path.read_text(encoding="utf-8")
    answer = extract_du_suite_coverage(trace_text, source_text, source_path)

    qa = {
        "question_kind": "coverage_prediction",
        "question": (
            "Use `test/qa/lane_du_suite_probe_test.py`, class `TestLaneDuSuiteProbeQA`, method "
            "`test_lane_du_suite_probe_cases`, and execute the full parametrized suite in that file (all cases). "
            "Tracing records call, line, and return for `yt_dlp/bind_lane.py::tube_digest` during those runs. "
            "For one completed call, process line events in order and build dynamic def-use triples "
            "(var, def_lineno, use_lineno) for locals and parameters of tube_digest: initialize last_def[v] to the "
            "function def line for each parameter v; at each executed line L, for each variable read on L in the "
            "source, if last_def has v, record (v, last_def[v], L); then for each variable written on L, set "
            "last_def[v] = L (uses before defs on the same line). Let U be the set of all distinct triples from all "
            "calls in the suite. Let R be the union of triple sets from the same rule applied to tube_digest run in "
            "isolation on inputs (0, \"\"), (1, \"x\"), (2, \"x\"), (0, \"ab\"), (1, \"ab\") in that order, using the "
            "same yt_dlp/bind_lane.py. Return all_du_pairs_covered true iff every triple in R appears at least once "
            "in U. Return missing_du_pairs as the list of triples in R but not in U, each as "
            "[var, def_lineno, use_lineno] sorted lexicographically by (var, def_lineno, use_lineno), or [] if "
            "all_du_pairs_covered is true."
        ),
        "template_answer": {
            "all_du_pairs_covered": "bool",
            "missing_du_pairs": [["str", "int", "int"]],
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
