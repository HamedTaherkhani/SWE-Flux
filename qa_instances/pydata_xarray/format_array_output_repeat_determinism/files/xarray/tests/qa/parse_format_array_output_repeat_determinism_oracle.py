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

TARGET_FUNCTION_IDENTIFIER = (
    "xarray.core.formatting.format_array_flat|||"
    "xarray/core/formatting.py::format_array_flat|||"
    "format_array_flat"
)


def _iter_identifier_tokens(func: str) -> list[str]:
    if "|||" in func:
        return [part.strip() for part in func.split("|||") if part.strip()]
    return [func.strip()]


def _short_name(func_token: str) -> str:
    rhs = func_token.split("::", 1)[-1]
    return rhs.rsplit(".", 1)[-1]


def _probe_function_exists(source_text: str) -> None:
    tree = ast.parse(source_text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "format_array_flat":
            return
    raise ValueError("format_array_flat not found.")


def _normalize_repr(value_repr: str) -> str:
    try:
        val = ast.literal_eval(value_repr)
    except Exception:
        return str(value_repr)
    return str(val)


def extract_determinism(trace_text: str, source_text: str) -> dict[str, object]:
    _probe_function_exists(source_text)

    events: list[tuple[int, dict[str, str]]] = []
    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not any(_short_name(token) == "format_array_flat" for token in _iter_identifier_tokens(func)):
            continue
        events.append((int(m.group("lineno")), ast.literal_eval(m.group("locals"))))

    if not events:
        raise ValueError("No format_array_flat line events found.")

    start_line = min(l for l, _ in events)
    per_call_outputs: list[str] = []
    current_last_output: str | None = None
    in_call = False

    for lineno, locals_map in events:
        if lineno == start_line:
            if in_call and current_last_output is not None:
                per_call_outputs.append(current_last_output)
            in_call = True
            current_last_output = None

        if "pprint_str" in locals_map:
            current_last_output = _normalize_repr(locals_map["pprint_str"])

    if in_call and current_last_output is not None:
        per_call_outputs.append(current_last_output)

    if len(per_call_outputs) < 5:
        raise ValueError(f"Expected at least 5 observed outputs, got {len(per_call_outputs)}.")

    repeated = per_call_outputs[:5]
    deterministic = all(v == repeated[0] for v in repeated)
    return {
        "function": TARGET_FUNCTION_IDENTIFIER,
        "repetitions": 5,
        "is_output_identical_every_time": deterministic,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/format_array_output_repeat_determinism/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/formatting.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/format_array_output_repeat_determinism/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_determinism(trace_text, source_text)

    qa = {
        "question_kind": "determinism_flakiness",
        "question": (
            "Use `xarray/tests/qa/format_array_output_repeat_determinism_test.py`, class "
            "`TestFormatArrayOutputRepeatDeterminismHardQA`, and execute the full suite in that "
            "file (both test methods). In that suite, `xarray/core/formatting.py::format_array_flat` "
            "is executed 5 times with identical input in part_a. Is the returned string identical "
            "across all 5 executions?"
        ),
        "template_answer": {
            "function": "str",
            "repetitions": "int",
            "is_output_identical_every_time": "bool",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
