#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/reflex/utils/serializers\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)

ALLOWED_FUNCS = {
    "reflex.utils.serializers.serialize",
    "reflex.utils.serializers.get_serializer",
    "reflex.utils.serializers.get_serializer_type",
    "reflex.utils.serializers.has_serializer",
    "reflex.utils.serializers.can_serialize",
    "reflex.utils.serializers.serialize_base",
    "reflex.utils.serializers.serialize_sequence",
    "reflex.utils.serializers.serialize_datetime",
    "reflex.utils.serializers.serialize_path",
    "reflex.utils.serializers.serialize_enum",
}


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for execution path extraction.")

    executed_path = []
    for match in matches:
        func = match.group("func")
        if func not in ALLOWED_FUNCS:
            continue
        executed_path.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": func,
                "line": int(match.group("lineno")),
            }
        )
    if not executed_path:
        raise ValueError("Trace had line events, but none matched the exact target functions.")
    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/serializers_dispatch_execution_path_lines/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/serializers_dispatch_execution_path_lines/oracle.json",
    )
    args = parser.parse_args()

    output = extract_execution_path(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/serializers_dispatch_execution_path_lines_test.py`, class "
            "`TestSerializersDispatchExecutionPathLinesQA`, method "
            "`test_serializers_dispatch_execution_path_lines_case`. The `DispatchPayload` instance is created "
            "at line 23, serializer availability is checked at lines 24-27, and lines 29-35 serialize the payload, "
            "a `Path`, a `datetime`, an enum member, and a tuple using `get_type=True`. Return the execution path "
            "only for line events in `reflex/utils/serializers.py`, and only for these functions: "
            "`reflex.utils.serializers.serialize`, `reflex.utils.serializers.get_serializer`, "
            "`reflex.utils.serializers.get_serializer_type`, `reflex.utils.serializers.has_serializer`, "
            "`reflex.utils.serializers.can_serialize`, `reflex.utils.serializers.serialize_base`, "
            "`reflex.utils.serializers.serialize_sequence`, `reflex.utils.serializers.serialize_datetime`, "
            "`reflex.utils.serializers.serialize_path`, and `reflex.utils.serializers.serialize_enum`. "
            "This execution exercises direct serializer lookup, subclass lookup, type conversion lookup, and multiple "
            "registered serializer functions. What is the exact ordered execution path as a list of objects with keys "
            "`file`, `func`, and `line`, including repeated lines?"
        ),
        "template_answer": {
            "executed_path": [{"file": "str", "func": "str", "line": "int"}]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
