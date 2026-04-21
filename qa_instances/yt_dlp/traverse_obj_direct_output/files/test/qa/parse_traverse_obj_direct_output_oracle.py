#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=return retval=(?P<retval>.+?) "
    r"locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _probe_function_exists(source_text: str) -> None:
    tree = ast.parse(source_text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "traverse_obj":
            return
    raise ValueError("traverse_obj not found.")


def extract_output(trace_text: str, source_text: str) -> dict[str, object]:
    _probe_function_exists(source_text)

    for m in RETURN_RE.finditer(trace_text):
        if not m.group("func").endswith(".traverse_obj"):
            continue

        retval = m.group("retval")
        try:
            value = ast.literal_eval(retval)
        except Exception as e:
            raise ValueError(f"Could not parse traverse_obj return value: {retval}") from e

        return {
            "target_function": "traverse_obj",
            "returned_value": value,
        }

    raise ValueError("No traverse_obj return event found in trace.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/traverse_obj_direct_output/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/yt_dlp/utils/traversal.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/traverse_obj_direct_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    answer = extract_output(trace_text, source_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/traverse_obj_direct_output_test.py`, class `TestTraverseObjDirectOutputQA`, "
            "method `test_traverse_obj_direct_output_case`. In this test, directly evaluate "
            "`yt_dlp/utils/traversal.py::traverse_obj` for the provided payload and path "
            "`(\"playlist\", \"entries\", ..., \"duration\", {int})`. What is the exact return value of "
            "`traverse_obj` for that direct call? Should `target_function` read `traverse_obj` and "
            "`returned_value` be that call's concrete `list[int]`?"
        ),
        "template_answer": {
            "target_function": "str",
            "returned_value": "list[int]",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
