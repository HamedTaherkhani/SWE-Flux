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

KEY_RE = re.compile(r"'([^']+)':")


def _target_loop_lineno(source_text: str) -> int:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "decompose_interp":
            fn = node
            break
    if fn is None:
        raise ValueError("decompose_interp not found.")

    for node in ast.walk(fn):
        if isinstance(node, ast.For):
            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
                if node.iter.func.id == "enumerate":
                    return node.lineno
    raise ValueError("Target enumerate loop not found.")


def _ordered_unique(seq: list[str]) -> list[str]:
    out: list[str] = []
    seen = set()
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_state(trace_text: str, source_text: str) -> dict[str, object]:
    _target_loop_lineno(source_text)  # structural validation that loop exists
    target_i = 4  # 5th iteration in 0-based enumerate
    current_i = None

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith(".decompose_interp"):
            continue

        locals_map = ast.literal_eval(m.group("locals"))
        if "i" in locals_map:
            try:
                current_i = ast.literal_eval(locals_map["i"])
            except Exception:
                current_i = None

        if "partial_indexes_coords" not in locals_map:
            continue
        if current_i != target_i:
            continue
        pic_repr = locals_map["partial_indexes_coords"]
        keys = _ordered_unique(KEY_RE.findall(pic_repr))
        return {
            "iteration_number": target_i + 1,
            "partial_indexes_coords_keys": keys,
        }

    raise ValueError("Could not find target loop state for the 5th iteration.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/decompose_interp_nth_iteration_state/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/missing.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/decompose_interp_nth_iteration_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_state(trace_text, source_text)

    qa = {
        "question_kind": "iterations",
        "question": (
            "Use `xarray/tests/qa/decompose_interp_nth_iteration_state_test.py`, class "
            "`TestDecomposeInterpNthIterationStateHardQA`, method "
            "`test_decompose_interp_nth_iteration_state_case`. "
            "At line 34, the test executes `list(xarray/core/missing.py::decompose_interp(indexes_coords))`. "
            "Inside `decompose_interp`, focus on the loop "
            "`for i, index_coords in enumerate(indexes_coords.items()):`. "
            "For the 5th iteration of that loop (i.e., `i == 4`), immediately after the statement "
            "`partial_indexes_coords.update([index_coords])` executes, what is the exact value of "
            "`partial_indexes_coords` in terms of its key sequence? Return the key order as "
            "`partial_indexes_coords_keys`."
        ),
        "template_answer": {
            "iteration_number": "int",
            "partial_indexes_coords_keys": ["str"],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
