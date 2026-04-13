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
    cls = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ProgressCalculator":
            cls = node
            break
    if cls is None:
        raise ValueError("ProgressCalculator not found.")

    fn = None
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_update":
            fn = node
            break
    if fn is None:
        raise ValueError("ProgressCalculator._update not found.")

    for node in ast.walk(fn):
        if isinstance(node, ast.If):
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Call)
                and isinstance(test.left.func, ast.Name)
                and test.left.func.id == "len"
                and len(test.left.args) == 1
                and isinstance(test.left.args[0], ast.Attribute)
                and isinstance(test.left.args[0].value, ast.Name)
                and test.left.args[0].value.id == "self"
                and test.left.args[0].attr == "_times"
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == 2
            ):
                return node.lineno
    raise ValueError("Target conditional `if len(self._times) < 2:` not found.")


def extract_state(trace_text: str, source_text: str) -> dict[str, object]:
    target_line = _target_line(source_text)
    cached_offset = None

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not (func.endswith(".ProgressCalculator._update") or func.endswith("._update")):
            continue
        lineno = int(m.group("lineno"))
        locals_map = ast.literal_eval(m.group("locals"))

        if "offset" in locals_map:
            cached_offset = ast.literal_eval(locals_map["offset"])

        if lineno == target_line and cached_offset is not None:
            return {
                "target_function": "ProgressCalculator._update",
                "specific_location": "if len(self._times) < 2:",
                "variable_name": "offset",
                "variable_state": cached_offset,
            }

    raise ValueError("Could not capture offset state at target conditional location.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/progress_offset_state_conditional/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/yt_dlp/utils/progress.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/progress_offset_state_conditional/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    answer = extract_state(trace_text, source_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/progress_offset_state_conditional_test.py`, class "
            "`TestProgressOffsetStateConditionalQA`, method `test_progress_offset_state_conditional_case`. "
            "In `yt_dlp/utils/progress.py`, inside `ProgressCalculator._update`, at the point where "
            "conditional `if len(self._times) < 2:` is evaluated, what is the exact value of variable "
            "`offset`? Should `specific_location` quote that conditional line and `variable_state` be "
            "the integer seen there?"
        ),
        "template_answer": {
            "target_function": "str",
            "specific_location": "str",
            "variable_name": "str",
            "variable_state": "int",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
