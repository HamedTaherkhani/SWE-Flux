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


def _return_line(source_text: str) -> int:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "calculate_dimensions":
            fn = node
            break
    if fn is None:
        raise ValueError("calculate_dimensions not found.")

    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "dims":
            return node.lineno
    raise ValueError("Could not locate `return dims` line.")


def _normalize_dims_repr(value_repr: str) -> str:
    d = ast.literal_eval(value_repr)
    if not isinstance(d, dict):
        raise ValueError("dims repr is not a dict.")
    return json.dumps(dict(sorted(d.items(), key=lambda kv: str(kv[0]))), sort_keys=True)


def extract_determinism(trace_text: str, source_text: str) -> dict[str, object]:
    _return_line(source_text)  # structural sanity check: function has return dims

    events: list[tuple[int, dict[str, str]]] = []
    for m in LINE_RE.finditer(trace_text):
        if not m.group("func").endswith(".calculate_dimensions"):
            continue
        events.append((int(m.group("lineno")), ast.literal_eval(m.group("locals"))))

    if not events:
        raise ValueError("No calculate_dimensions line events found.")

    start_line = min(l for l, _ in events)
    per_call_outputs: list[str] = []
    current_last_dims: str | None = None
    in_call = False

    for lineno, locals_map in events:
        if lineno == start_line:
            if in_call and current_last_dims is not None:
                per_call_outputs.append(current_last_dims)
            in_call = True
            current_last_dims = None

        if "dims" in locals_map:
            current_last_dims = _normalize_dims_repr(locals_map["dims"])

    if in_call and current_last_dims is not None:
        per_call_outputs.append(current_last_dims)

    if len(per_call_outputs) < 5:
        raise ValueError(f"Expected at least 5 observed outputs, got {len(per_call_outputs)}.")

    repeated = per_call_outputs[:5]
    deterministic = all(v == repeated[0] for v in repeated)
    return {
        "function": "calculate_dimensions",
        "repetitions": 5,
        "is_output_identical_every_time": deterministic,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/dimensions_repeat_determinism/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/variable.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/dimensions_repeat_determinism/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_determinism(trace_text, source_text)

    qa = {
        "question_kind": "determinism_flakiness",
        "question": (
            "Use `xarray/tests/qa/dimensions_repeat_determinism_test.py`, class "
            "`TestDimensionsRepeatDeterminismHardQA`, and execute the full suite in that file "
            "(both test methods). In that suite, "
            "`xarray/core/variable.py::calculate_dimensions` is executed 5 times with identical input. "
            "Is the returned value identical across all 5 executions?"
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
