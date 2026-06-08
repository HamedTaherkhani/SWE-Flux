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


def _target_line(source_text: str) -> int:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_dataset_concat":
            fn = node
            break
    if fn is None:
        raise ValueError("_dataset_concat not found.")

    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "variable_index" for t in node.targets):
                return node.lineno
    raise ValueError("`variable_index` assignment line not found.")


def _parse_array_repr(value_repr: str) -> list[int]:
    nums = [int(n) for n in re.findall(r"-?\d+", value_repr)]
    return nums


def extract_state(trace_text: str, source_text: str) -> dict[str, object]:
    target_line = _target_line(source_text)
    seen_target = False
    current_name: str | None = None
    current_variable_index: list[int] | None = None

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith("._dataset_concat"):
            continue
        lineno = int(m.group("lineno"))
        locals_map = ast.literal_eval(m.group("locals"))

        if "name" in locals_map:
            try:
                current_name = ast.literal_eval(locals_map["name"])
            except Exception:
                current_name = None

        if lineno == target_line:
            seen_target = True

        if seen_target and "variable_index" in locals_map:
            current_variable_index = _parse_array_repr(locals_map["variable_index"])
            if current_name == "temp":
                return {
                    "target_variable_name": "temp",
                    "variable_index_after_masking": current_variable_index,
                }

    raise ValueError("Could not capture target variable_index state for `temp`.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/concat_missing_var_index_state/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/concat.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/concat_missing_var_index_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_state(trace_text, source_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `xarray/tests/qa/concat_missing_var_index_state_test.py`, class "
            "`TestConcatMissingVarIndexStateHardQA`, method "
            "`test_concat_missing_var_index_state_case`. During this execution, inspect "
            "`_dataset_concat` in the concat module (`xarray/core/concat.py` or "
            "`xarray/structure/concat.py`, depending on version). In the loop "
            "`for name in vars_order:`, when "
            "`name == 'temp'`, what is the exact value of `variable_index` immediately after the "
            "statement `variable_index = concat_index[variable_index_mask]` executes?"
        ),
        "template_answer": {
            "target_variable_name": "str",
            "variable_index_after_masking": ["int"],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
