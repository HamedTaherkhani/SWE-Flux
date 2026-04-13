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
PATH_RE = re.compile(r"(?:PosixPath|WindowsPath)\('(?P<p>.*)'\)")


def _target_line(source_text: str) -> int:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "candidate_plugin_paths":
            fn = node
            break
    if fn is None:
        raise ValueError("candidate_plugin_paths not found.")

    for node in ast.walk(fn):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                call = test.operand
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == "candidate_path"
                    and call.func.attr == "is_dir"
                ):
                    return node.lineno
    raise ValueError("Target line `if not candidate_path.is_dir():` not found.")


def _parse_candidate_path(value_repr: str) -> str:
    m = PATH_RE.search(value_repr)
    if m:
        return m.group("p")
    return value_repr


def extract_state(trace_text: str, source_text: str) -> dict[str, object]:
    target_line = _target_line(source_text)
    cached_candidate = None
    cached_candidate_path = None

    for m in LINE_RE.finditer(trace_text):
        if not m.group("func").endswith(".candidate_plugin_paths"):
            continue

        locals_map = ast.literal_eval(m.group("locals"))
        lineno = int(m.group("lineno"))
        if "candidate" in locals_map:
            cached_candidate = ast.literal_eval(locals_map["candidate"])
        if "candidate_path" in locals_map:
            cached_candidate_path = _parse_candidate_path(locals_map["candidate_path"])

        # In some versions, locals are emitted on nearby lines (assignment before
        # the guard), not exactly on the guard line itself.
        if lineno >= target_line and cached_candidate is not None and cached_candidate_path is not None:
            return {
                "target_function": "candidate_plugin_paths",
                "specific_location": "if not candidate_path.is_dir():",
                "input_variable_states": {
                    "candidate": cached_candidate,
                    "candidate_path": cached_candidate_path,
                },
            }

    raise ValueError("Could not capture candidate/candidate_path at target location.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/plugin_candidate_input_state_indirect/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/yt_dlp/plugins.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/plugin_candidate_input_state_indirect/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    answer = extract_state(trace_text, source_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/plugin_candidate_input_state_indirect_test.py`, class "
            "`TestPluginCandidateInputStateIndirectQA`, method "
            "`test_plugin_candidate_input_state_indirect_case`. This test calls "
            "`PluginFinder.search_locations` in `yt_dlp/plugins.py`, which indirectly invokes "
            "`candidate_plugin_paths`. At the specific location `if not candidate_path.is_dir():` "
            "inside `candidate_plugin_paths`, what are the exact states of input variables `candidate` "
            "and `candidate_path`? Should `target_function` name `candidate_plugin_paths`, "
            "`specific_location` quote that `is_dir` guard, and `input_variable_states` stringify each "
            "argument exactly as observed?"
        ),
        "template_answer": {
            "target_function": "str",
            "specific_location": "str",
            "input_variable_states": {
                "candidate": "str",
                "candidate_path": "str",
            },
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
