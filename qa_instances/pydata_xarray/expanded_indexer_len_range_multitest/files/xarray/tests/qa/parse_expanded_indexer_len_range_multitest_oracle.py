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


def _target_lines(source_text: str) -> tuple[int, int]:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "expanded_indexer":
            fn = node
            break
    if fn is None:
        raise ValueError("expanded_indexer not found.")

    start_line = fn.body[0].lineno
    cond_line = None
    for node in ast.walk(fn):
        if isinstance(node, ast.If):
            expr = ast.unparse(node.test).replace(" ", "")
            if expr == "len(new_key)>ndim":
                cond_line = node.lineno
                break
    if cond_line is None:
        raise ValueError("Target condition `if len(new_key) > ndim` not found.")
    return start_line, cond_line


def _safe_parse_locals(raw: str) -> dict[str, str]:
    data = ast.literal_eval(raw)
    return {str(k): str(v) for k, v in data.items()}


def _new_key_len(value_repr: str) -> int:
    try:
        value = eval(value_repr, {"__builtins__": {}, "slice": slice})
        if isinstance(value, (list, tuple)):
            return len(value)
    except Exception:
        pass

    s = value_repr.strip()
    if s == "[]":
        return 0
    if s.startswith("[") and s.endswith("]"):
        depth = 0
        count = 1
        for ch in s[1:-1]:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "," and depth == 0:
                count += 1
        return count
    raise ValueError(f"Unable to parse new_key repr: {value_repr!r}")


def extract_range(trace_text: str, source_text: str) -> dict[str, object]:
    start_line, cond_line = _target_lines(source_text)
    cached_new_key: str | None = None
    observed: list[int] = []

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith(".expanded_indexer"):
            continue
        lineno = int(m.group("lineno"))
        locals_map = _safe_parse_locals(m.group("locals"))

        if lineno == start_line:
            cached_new_key = None
        if "new_key" in locals_map:
            cached_new_key = locals_map["new_key"]

        if lineno == cond_line and cached_new_key is not None:
            observed.append(_new_key_len(cached_new_key))

    if not observed:
        raise ValueError("No `len(new_key)` observations found at target condition line.")

    return {
        "variable": "len(new_key)",
        "minimum": min(observed),
        "maximum": max(observed),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/expanded_indexer_len_range_multitest/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/indexing.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/expanded_indexer_len_range_multitest/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_range(trace_text, source_text)

    qa = {
        "question_kind": "value_range_analysis",
        "question": (
            "Use `xarray/tests/qa/expanded_indexer_len_range_multitest_test.py`, class "
            "`TestExpandedIndexerLenRangeMultitestHardQA`, and execute the full suite in that file "
            "(both test methods). During this suite, in `xarray/core/indexing.py::expanded_indexer`, "
            "focus on the conditional statement `if len(new_key) > ndim:`. "
            "Across all evaluations of that condition in the suite, what is the observed range "
            "(minimum and maximum) of the variable expression `len(new_key)` immediately before "
            "the condition is checked?"
        ),
        "template_answer": {
            "variable": "str",
            "minimum": "int",
            "maximum": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
