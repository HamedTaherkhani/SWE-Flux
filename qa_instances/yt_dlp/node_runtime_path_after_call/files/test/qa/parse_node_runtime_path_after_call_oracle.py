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
        if isinstance(node, ast.FunctionDef) and node.name == "format_text":
            fn = node
            break
    if fn is None:
        raise ValueError("format_text not found.")

    for i, node in enumerate(fn.body):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "tokens"
            and isinstance(node.value, ast.Call)
        ):
            if i + 1 < len(fn.body):
                return fn.body[i + 1].lineno
            return node.lineno
    raise ValueError("Assignment `tokens = f.strip().split()` not found.")


def extract_state(trace_text: str, source_text: str) -> dict[str, object]:
    probe_line = _target_line(source_text)
    cached_tokens = None

    for m in LINE_RE.finditer(trace_text):
        if not m.group("func").endswith(".format_text"):
            continue

        locals_map = ast.literal_eval(m.group("locals"))
        lineno = int(m.group("lineno"))

        if "tokens" in locals_map:
            cached_tokens = ast.literal_eval(locals_map["tokens"])

        if lineno >= probe_line and cached_tokens is not None:
            return {
                "target_function": "format_text",
                "after_function_call": "tokens = f.strip().split()",
                "variable_name": "tokens",
                "variable_state": cached_tokens,
            }

    raise ValueError("Could not capture `tokens` state after split() call.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/node_runtime_path_after_call/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/yt_dlp/minicurses.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/node_runtime_path_after_call/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    answer = extract_state(trace_text, source_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/node_runtime_path_after_call_test.py`, class `TestNodeRuntimePathAfterCallQA`, "
            "method `test_node_runtime_path_after_call_case`. In `yt_dlp/minicurses.py`, inside "
            "`format_text`, after the function call `tokens = f.strip().split()`, what is the exact "
            "state of variable `tokens`? Should `after_function_call` reproduce that assignment line and "
            "should `variable_state` list every token string in order?"
        ),
        "template_answer": {
            "target_function": "str",
            "after_function_call": "str",
            "variable_name": "str",
            "variable_state": "list[str]",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
