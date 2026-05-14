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
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)


def _target_loop_lineno(source_text: str) -> int:
    tree = ast.parse(source_text)
    func_node = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "calculate_dimensions":
            func_node = node
            break
    if func_node is None:
        raise ValueError("Could not find calculate_dimensions in source file.")

    for node in ast.walk(func_node):
        if isinstance(node, ast.For):
            if isinstance(node.iter, ast.Call):
                callee = node.iter.func
                if isinstance(callee, ast.Name) and callee.id == "zip":
                    return node.lineno
    raise ValueError("Could not find target for-loop line in calculate_dimensions.")


def extract_iterations(trace_text: str, source_text: str) -> dict[str, int]:
    loop_lineno = _target_loop_lineno(source_text)
    count = 0
    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith(".calculate_dimensions"):
            continue
        if int(m.group("lineno")) == loop_lineno:
            count += 1

    if count == 0:
        raise ValueError("Could not find target loop line events in trace log.")
    return {"loop_iteration_count": count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/calculate_dimensions_loop_iterations/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/variable.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/calculate_dimensions_loop_iterations/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_iterations(trace_text, source_text)

    qa = {
        "question_kind": "C3_Loops",
        "question": (
            "Use `xarray/tests/qa/calculate_dimensions_loop_iterations_test.py`, class "
            "`TestCalculateDimensionsLoopIterationsHardQA`, method "
            "`test_calculate_dimensions_loop_iterations_case`. "
            "At line 19, the test calls `xarray/core/variable.py::calculate_dimensions` with a mapping "
            "of six variables. Inside `calculate_dimensions`, focus on the inner loop "
            "`for dim, size in zip(var.dims, var.shape):`. During the full execution of this test method, "
            "how many iterations does that specific inner loop execute in total?"
        ),
        "template_answer": {"loop_iteration_count": "int"},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
