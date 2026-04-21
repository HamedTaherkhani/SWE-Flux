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
        if isinstance(node, ast.ClassDef) and node.name == "JSInterpreter":
            cls = node
            break
    if cls is None:
        raise ValueError("JSInterpreter not found.")

    fn = None
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_separate_at_paren":
            fn = node
            break
    if fn is None:
        raise ValueError("JSInterpreter._separate_at_paren not found.")

    for node in fn.body:
        if isinstance(node, ast.If):
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Call)
                and isinstance(test.left.func, ast.Name)
                and test.left.func.id == "len"
                and len(test.left.args) == 1
                and isinstance(test.left.args[0], ast.Name)
                and test.left.args[0].id == "separated"
            ):
                return node.lineno
    raise ValueError("Target line `if len(separated) < 2:` not found.")


def extract_size(trace_text: str, source_text: str) -> dict[str, object]:
    target_line = _target_line(source_text)
    cached_separated = None

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not (func.endswith(".JSInterpreter._separate_at_paren") or func.endswith("._separate_at_paren")):
            continue

        locals_map = ast.literal_eval(m.group("locals"))
        lineno = int(m.group("lineno"))

        if "separated" in locals_map:
            cached_separated = ast.literal_eval(locals_map["separated"])

        if lineno == target_line and isinstance(cached_separated, list):
            return {
                "target_function": "JSInterpreter._separate_at_paren",
                "specific_location": "if len(separated) < 2:",
                "array_variable": "separated",
                "size": len(cached_separated),
            }

    raise ValueError("Could not capture size of `separated` at target line.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/separate_list_size_line_probe/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/yt_dlp/jsinterp.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/separate_list_size_line_probe/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    answer = extract_size(trace_text, source_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/separate_list_size_line_probe_test.py`, class "
            "`TestSeparateListSizeLineProbeQA`, method "
            "`test_separate_list_size_line_probe_case`. In `yt_dlp/jsinterp.py`, inside "
            "`JSInterpreter._separate_at_paren`, at the line `if len(separated) < 2:`, what is the "
            "size of array/list variable `separated`? Should your structured answer put the traced "
            "callable in `target_function`, that `if len(separated) < 2:` line in `specific_location`, "
            "the list's name in `array_variable`, and the integer length in `size`?"
        ),
        "template_answer": {
            "target_function": "str",
            "specific_location": "str",
            "array_variable": "str",
            "size": "int",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
