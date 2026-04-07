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


def _probe_function_exists(source_text: str) -> None:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "reindex_variables":
            fn = node
            break
    if fn is None:
        raise ValueError("reindex_variables not found.")

    # Structural probe only; avoids brittle line-number assumptions.
    return None


def extract_nth_iteration_value(trace_text: str, source_text: str) -> dict[str, object]:
    _probe_function_exists(source_text)
    iteration = 0

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith(".reindex_variables"):
            continue
        locals_map = ast.literal_eval(m.group("locals"))

        # Cross-version robust signal for the loop iteration start:
        # in this loop, each iteration has both `dim` and `indxr` bound.
        if "dim" in locals_map and "indxr" in locals_map:
            iteration += 1
            if iteration == 2:
                try:
                    dim_value = ast.literal_eval(locals_map["dim"])
                except Exception:
                    dim_value = str(locals_map["dim"]).strip("'")
                return {
                    "iteration_number": 2,
                    "variable_name": "dim",
                    "value_at_iteration_start": dim_value,
                }

    raise ValueError("Could not capture `dim` at start of 2nd loop iteration.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/reindex_dim_nth_iteration_value/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/alignment.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/reindex_dim_nth_iteration_value/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_nth_iteration_value(trace_text, source_text)

    qa = {
        "question_kind": "iterations",
        "question": (
            "Use `xarray/tests/qa/reindex_dim_nth_iteration_value_test.py`, class "
            "`TestReindexDimNthIterationValueHardQA`, method "
            "`test_reindex_dim_nth_iteration_value_case`. During this execution, inspect "
            "`reindex_variables` in the alignment module (`xarray/core/alignment.py` or "
            "`xarray/structure/alignment.py`, depending on version). Focus on the loop "
            "`for dim, indxr in dim_pos_indexers.items():`. At the start of the 2nd iteration of "
            "that loop, what is the exact value of variable `dim`?"
        ),
        "template_answer": {
            "iteration_number": "int",
            "variable_name": "str",
            "value_at_iteration_start": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
