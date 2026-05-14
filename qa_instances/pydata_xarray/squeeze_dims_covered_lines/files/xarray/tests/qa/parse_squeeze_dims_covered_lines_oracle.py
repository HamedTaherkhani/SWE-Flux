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

TARGET_FUNCTION_IDENTIFIER = (
    "xarray.core.common.get_squeeze_dims|||"
    "xarray/core/common.py::get_squeeze_dims|||"
    "get_squeeze_dims"
)


def _iter_identifier_tokens(func: str) -> list[str]:
    if "|||" in func:
        return [part.strip() for part in func.split("|||") if part.strip()]
    return [func.strip()]


def _short_name(func_token: str) -> str:
    rhs = func_token.split("::", 1)[-1]
    return rhs.rsplit(".", 1)[-1]


def _function_line_range(source_text: str) -> tuple[int, int]:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "get_squeeze_dims":
            fn = node
            break
    if fn is None:
        raise ValueError("get_squeeze_dims not found.")

    all_nodes = [n for n in ast.walk(fn) if hasattr(n, "lineno")]
    start = fn.lineno
    end = max(n.lineno for n in all_nodes)
    return start, end


def extract_covered_lines(trace_text: str, source_text: str) -> dict[str, object]:
    start, end = _function_line_range(source_text)
    covered: set[int] = set()

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not any(_short_name(token) == "get_squeeze_dims" for token in _iter_identifier_tokens(func)):
            continue
        lineno = int(m.group("lineno"))
        if start <= lineno <= end:
            covered.add(lineno)

    if not covered:
        raise ValueError("No covered lines captured for get_squeeze_dims.")

    return {
        "target_function": TARGET_FUNCTION_IDENTIFIER,
        "covered_lines": sorted(covered),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/squeeze_dims_covered_lines/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/common.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/squeeze_dims_covered_lines/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_covered_lines(trace_text, source_text)

    qa = {
        "question_kind": "M1_IntraProceduralCFG",
        "question": (
            "Use `xarray/tests/qa/squeeze_dims_covered_lines_test.py`, class "
            "`TestSqueezeDimsCoveredLinesHardQA`, and execute the full suite in that file "
            "(both test methods). "
            "With those exact inputs/calls, which line numbers inside "
            "`xarray/core/common.py::get_squeeze_dims` are executed at least once? "
            "Return the unique covered line numbers in ascending order."
        ),
        "template_answer": {
            "target_function": "str",
            "covered_lines": ["int"],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
