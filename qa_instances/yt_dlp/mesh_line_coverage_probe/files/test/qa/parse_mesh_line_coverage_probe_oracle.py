#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"(?m)(?:^\d{4}-\d{2}-\d{2} .+? )?"
    r"(?P<path>[^:]+):(?P<lineno>\d+) (?P<func>\S+) event=line ",
)


def _function_line_range(source_text: str) -> tuple[int, int]:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_mesh":
            fn = node
            break
    if fn is None:
        raise ValueError("resolve_mesh not found.")

    all_nodes = [n for n in ast.walk(fn) if hasattr(n, "lineno")]
    start = int(fn.lineno)
    end = max(int(getattr(n, "end_lineno", n.lineno)) for n in all_nodes)
    return start, end


def extract_covered_lines(trace_text: str, source_text: str) -> dict[str, object]:
    start, end = _function_line_range(source_text)
    covered: set[int] = set()

    for m in LINE_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith("yt_dlp/switch_mesh.py"):
            continue
        func = m.group("func")
        if func != "yt_dlp.switch_mesh.resolve_mesh" and not func.endswith(".resolve_mesh"):
            continue
        lineno = int(m.group("lineno"))
        if start <= lineno <= end:
            covered.add(lineno)

    if not covered:
        raise ValueError("No covered lines captured for resolve_mesh.")

    return {
        "target_function": "resolve_mesh",
        "covered_lines": sorted(covered),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/mesh_line_coverage_probe/trace.log",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/switch_mesh.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/mesh_line_coverage_probe/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source).read_text(encoding="utf-8")
    out = extract_covered_lines(trace_text, source_text)

    qa = {
        "question_kind": "coverage_prediction",
        "question": (
            "Use `test/qa/mesh_line_coverage_probe_test.py` and execute the full parametrized test suite "
            "in that file (all cases). With those exact calls to `resolve_mesh`, which unique line numbers "
            "inside `yt_dlp/switch_mesh.py::resolve_mesh` are executed at least once across the entire "
            "suite (union of coverage across all tests)? Return `target_function` and `covered_lines`, "
            "where `covered_lines` is sorted ascending and includes only lines within the `resolve_mesh` "
            "function body (from its `def` line through the last executable line of that function)."
        ),
        "template_answer": {
            "target_function": "str",
            "covered_lines": ["int"],
        },
        "oracle_answer": {
            "target_function": out["target_function"],
            "covered_lines": out["covered_lines"],
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
