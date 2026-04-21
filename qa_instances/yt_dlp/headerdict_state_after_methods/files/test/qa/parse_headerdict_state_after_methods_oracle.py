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


def _probe_method_exists(source_text: str) -> None:
    tree = ast.parse(source_text)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "HTTPHeaderDict":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "sensitive":
                    return
    raise ValueError("HTTPHeaderDict.sensitive not found.")


def _sorted_dict_repr(d: dict) -> dict:
    return {k: d[k] for k in sorted(d.keys(), key=str)}


def extract_state(trace_text: str, source_text: str) -> dict[str, object]:
    _probe_method_exists(source_text)

    last_payload = None
    for m in RETURN_RE.finditer(trace_text):
        func = m.group("func")
        if not (func.endswith(".HTTPHeaderDict.sensitive") or func.endswith(".sensitive")):
            continue

        retval = ast.literal_eval(m.group("retval"))
        if not isinstance(retval, dict):
            continue

        # HTTPHeaderDict stores normalized title-cased keys internally.
        headers_map = {str(k).title(): str(v) for k, v in retval.items()}
        sensitive_map = {str(k): str(v) for k, v in retval.items()}

        last_payload = {
            "object_name": "headers",
            "method_sequence": [
                "update",
                "__setitem__",
                "setdefault",
                "setdefault",
                "pop",
                "sensitive",
            ],
            "state_after_methods": {
                "headers_mapping": _sorted_dict_repr(headers_map),
                "sensitive_mapping": _sorted_dict_repr(sensitive_map),
            },
        }

    if last_payload is None:
        raise ValueError("Could not extract HTTPHeaderDict state from sensitive() return trace.")
    return last_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/headerdict_state_after_methods/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/yt_dlp/utils/networking.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/headerdict_state_after_methods/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    answer = extract_state(trace_text, source_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/headerdict_state_after_methods_test.py`, class "
            "`TestHeaderdictStateAfterMethodsQA`, method `test_headerdict_state_after_methods_case`. In "
            "`yt_dlp/utils/networking.py`, for object `headers` of class `HTTPHeaderDict`, after "
            "executing the method sequence `update`, `__setitem__`, `setdefault`, `setdefault`, `pop`, "
            "and then `sensitive`, what are the exact final states of the internal header mapping "
            "(`headers`) and the case-sensitive mapping returned by `headers.sensitive()`? Should "
            "`state_after_methods.headers_mapping` mirror the ordinary mapping and `sensitive_mapping` "
            "match the dict from `headers.sensitive()`?"
        ),
        "template_answer": {
            "object_name": "str",
            "method_sequence": "list[str]",
            "state_after_methods": {
                "headers_mapping": "dict[str,str]",
                "sensitive_mapping": "dict[str,str]",
            },
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
