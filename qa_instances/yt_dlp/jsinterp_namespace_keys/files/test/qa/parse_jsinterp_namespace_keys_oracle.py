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


def _probe_line(source_text: str) -> int:
    tree = ast.parse(source_text)
    cls = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "JSInterpreter":
            cls = node
            break
    if cls is None:
        raise ValueError("JSInterpreter class not found.")

    fn = None
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_named_object":
            fn = node
            break
    if fn is None:
        raise ValueError("JSInterpreter._named_object not found.")

    for node in fn.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Subscript)
            and isinstance(node.targets[0].value, ast.Name)
            and node.targets[0].value.id == "namespace"
            and isinstance(node.targets[0].slice, ast.Name)
            and node.targets[0].slice.id == "name"
        ):
            # next statement after namespace[name] = obj
            return node.lineno + 1
    raise ValueError("Target assignment `namespace[name] = obj` not found.")


def extract_keys(trace_text: str, source_text: str) -> dict[str, object]:
    probe_line = _probe_line(source_text)
    cached_namespace = None

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not (func.endswith(".JSInterpreter._named_object") or func.endswith("._named_object")):
            continue
        lineno = int(m.group("lineno"))
        locals_map = ast.literal_eval(m.group("locals"))

        if "namespace" in locals_map:
            ns = ast.literal_eval(locals_map["namespace"])
            if isinstance(ns, dict):
                cached_namespace = ns

        if lineno >= probe_line and cached_namespace is not None:
            keys_sorted = sorted(str(k) for k in cached_namespace.keys())
            return {
                "target_function": "JSInterpreter._named_object",
                "dictionary_variable": "namespace",
                "dictionary_keys": keys_sorted,
            }

    raise ValueError("Could not capture namespace dictionary keys after target assignment.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/jsinterp_namespace_keys/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/yt_dlp/jsinterp.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/jsinterp_namespace_keys/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    answer = extract_keys(trace_text, source_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/jsinterp_namespace_keys_test.py`, class `TestJSInterpNamespaceKeysQA`, "
            "method `test_jsinterp_namespace_keys_case`. In `yt_dlp/jsinterp.py`, inside "
            "`JSInterpreter._named_object`, after executing `namespace[name] = obj`, what exact keys "
            "does dictionary variable `namespace` hold? Should `dictionary_keys` list those key strings "
            "in runtime order?"
        ),
        "template_answer": {
            "target_function": "str",
            "dictionary_variable": "str",
            "dictionary_keys": "list[str]",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
