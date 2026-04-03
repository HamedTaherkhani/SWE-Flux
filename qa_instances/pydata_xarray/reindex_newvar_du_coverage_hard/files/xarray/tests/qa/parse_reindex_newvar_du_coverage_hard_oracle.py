#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _collect_du_sites(source_text: str) -> tuple[list[int], list[int], int]:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "reindex_variables":
            fn = node
            break
    if fn is None:
        raise ValueError("reindex_variables not found.")

    def_lines: list[int] = []
    use_lines: list[int] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "new_var":
                    def_lines.append(node.lineno)
            for sub in ast.walk(node.value):
                if isinstance(sub, ast.Name) and sub.id == "new_var":
                    use_lines.append(node.lineno)

    def_lines = sorted(set(def_lines))
    use_lines = sorted(set(use_lines))
    if not def_lines or not use_lines:
        raise ValueError("Could not locate def/use lines for new_var.")
    return def_lines, use_lines, fn.body[0].lineno


def extract_du_coverage(trace_text: str, source_text: str) -> dict[str, object]:
    def_lines, use_lines, fn_start = _collect_du_sites(source_text)
    covered_pairs: set[tuple[int, int]] = set()

    current_def: int | None = None
    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith(".reindex_variables"):
            continue
        lineno = int(m.group("lineno"))

        if lineno == fn_start:
            current_def = None

        if lineno in def_lines:
            current_def = lineno

        if lineno in use_lines and current_def is not None:
            covered_pairs.add((current_def, lineno))

    all_pairs = {(d, u) for d in def_lines for u in use_lines}
    return {
        "variable": "new_var",
        "total_du_pairs": len(all_pairs),
        "covered_du_pairs": len(covered_pairs),
        "all_du_pairs_covered": covered_pairs == all_pairs,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/reindex_newvar_du_coverage_hard/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/alignment.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/reindex_newvar_du_coverage_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_du_coverage(trace_text, source_text)

    qa = {
        "question_kind": "coverage_prediction",
        "question": (
            "Use `xarray/tests/qa/reindex_newvar_du_coverage_hard_test.py`, class "
            "`TestReindexNewVarDUCoverageHardQA`, and execute the full suite in that file "
            "(both test methods). During this execution, inspect "
            "`reindex_variables` in the alignment module (`xarray/core/alignment.py` or "
            "`xarray/structure/alignment.py`, depending on version). Focus on DU-pairs for variable "
            "`new_var` where definitions are assignments to `new_var` and uses are reads of `new_var` "
            "on the right-hand side. Are all such DU-pairs covered by this test suite?"
        ),
        "template_answer": {
            "variable": "str",
            "total_du_pairs": "int",
            "covered_du_pairs": "int",
            "all_du_pairs_covered": "bool",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
