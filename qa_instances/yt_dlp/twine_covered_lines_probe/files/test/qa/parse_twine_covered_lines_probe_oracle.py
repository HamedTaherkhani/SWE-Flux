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
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_knot":
            fn = node
            break
    if fn is None:
        raise ValueError("resolve_knot not found.")

    all_nodes = [n for n in ast.walk(fn) if hasattr(n, "lineno")]
    start = int(fn.lineno)
    end = max(int(getattr(n, "end_lineno", n.lineno)) for n in all_nodes)
    return start, end


def extract_covered_lines(trace_text: str, source_text: str) -> dict[str, object]:
    start, end = _function_line_range(source_text)
    covered: set[int] = set()

    for m in LINE_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith("yt_dlp/knot_table.py"):
            continue
        func = m.group("func")
        if func != "yt_dlp.knot_table.resolve_knot" and not func.endswith(".resolve_knot"):
            continue
        lineno = int(m.group("lineno"))
        if start <= lineno <= end:
            covered.add(lineno)

    if not covered:
        raise ValueError("No covered lines captured for resolve_knot.")

    return {
        "target_function": "resolve_knot",
        "covered_lines": sorted(covered),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/twine_covered_lines_probe/trace.log",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/knot_table.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/twine_covered_lines_probe/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source).read_text(encoding="utf-8")
    out = extract_covered_lines(trace_text, source_text)

    qa = {
        "question_kind": "coverage_prediction",
        "question": (
            "Use `test/qa/twine_covered_lines_probe_test.py`, class `TestTwineCoveredLinesQA`, method "
            "`test_twine_covered_lines_probe_cases`, and execute the full parametrized suite in that file "
            "(all cases; more than fifteen rows). With those exact calls to `resolve_knot`, which unique line "
            "numbers inside `yt_dlp/knot_table.py::resolve_knot` are executed at least once across the entire "
            "suite (union of line coverage across all tests)? Return `target_function` and `covered_lines`, "
            "where `covered_lines` is sorted ascending and includes only lines from the `def resolve_knot` line "
            "through the last executable line of that function (including executed condition lines; omit only "
            "lines that never receive a `line` trace event in any test)."
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
