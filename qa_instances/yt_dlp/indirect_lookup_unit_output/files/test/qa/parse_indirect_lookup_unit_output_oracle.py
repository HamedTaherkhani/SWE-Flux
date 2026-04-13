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


def _probe_lookup_unit_table(source_text: str) -> None:
    tree = ast.parse(source_text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "lookup_unit_table":
            return
    raise ValueError("lookup_unit_table not found.")


def extract_output(trace_text: str, source_text: str) -> dict[str, object]:
    _probe_lookup_unit_table(source_text)

    events: list[tuple[int, dict[str, str]]] = []
    for m in LINE_RE.finditer(trace_text):
        if not m.group("func").endswith(".lookup_unit_table"):
            continue
        events.append((int(m.group("lineno")), ast.literal_eval(m.group("locals"))))

    if not events:
        raise ValueError("No lookup_unit_table events found in trace.")

    start_line = min(l for l, _ in events)
    calls: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for lineno, locals_map in events:
        if lineno == start_line:
            if current is not None:
                calls.append(current)
            current = {}

        if current is None:
            current = {}

        if "s" in locals_map:
            current["s"] = ast.literal_eval(locals_map["s"])
        if "num" in locals_map:
            current["num"] = ast.literal_eval(locals_map["num"])
        if "mult" in locals_map:
            current["mult"] = ast.literal_eval(locals_map["mult"])

    if current is not None:
        calls.append(current)

    target_call = None
    for c in calls:
        if c.get("s") == "12.5M":
            target_call = c
            break
    if target_call is None:
        raise ValueError("Could not find lookup_unit_table call for input '12.5M'.")

    if "num" not in target_call or "mult" not in target_call:
        raise ValueError("Missing num/mult locals for target lookup_unit_table call.")

    output = round(float(target_call["num"]) * int(target_call["mult"]))
    return {
        "target_function": "lookup_unit_table",
        "indirect_entry_function": "parse_bytes",
        "returned_value": int(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/indirect_lookup_unit_output/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/yt_dlp/utils/_utils.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/indirect_lookup_unit_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    answer = extract_output(trace_text, source_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/indirect_lookup_unit_output_test.py`, class `TestIndirectLookupUnitOutputQA`, "
            "method `test_indirect_lookup_unit_output_case`. The test calls "
            "`yt_dlp/utils/_utils.py::parse_bytes`, which internally calls "
            "`yt_dlp/utils/_utils.py::lookup_unit_table`. For the invocation where input string is "
            "`12.5M`, what exact value does `lookup_unit_table` return? Should `indirect_entry_function` "
            "name the outer `parse_bytes` caller, `target_function` name `lookup_unit_table`, and "
            "`returned_value` hold that inner numeric result?"
        ),
        "template_answer": {
            "target_function": "str",
            "indirect_entry_function": "str",
            "returned_value": "int",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
