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
    r"(?P<func>[^ ]+) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

ARRAY_RE = re.compile(r"array\(\[([^\]]*)\]\)")


def _parse_array_of_numbers(text: str) -> list[int | float]:
    m = ARRAY_RE.search(text)
    if m is None:
        raise ValueError(f"Could not parse array from: {text!r}")
    values = []
    for token in [x.strip() for x in m.group(1).split(",") if x.strip()]:
        if "." in token:
            values.append(float(token))
        else:
            values.append(int(token))
    return values


def _parse_list_of_arrays(text: str) -> list[list[int]]:
    arrays = ARRAY_RE.findall(text)
    if not arrays:
        literal = ast.literal_eval(text)
        if isinstance(literal, list) and all(isinstance(row, list) for row in literal):
            return [[int(x) for x in row] for row in literal]
        raise ValueError("Could not parse list of arrays for code_list.")
    out: list[list[int]] = []
    for arr in arrays:
        values = [int(x.strip()) for x in arr.split(",") if x.strip()]
        out.append(values)
    return out


def extract_loop_state(trace_text: str) -> dict[str, object]:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find to_index line events in trace log.")

    saw_target_ordered_dims = False
    repeat_counts_raw = None
    tile_counts_raw = None
    code_list_raw = None
    for match in matches:
        func = match.group("func")
        if not func.endswith(".to_index"):
            continue

        locals_map = ast.literal_eval(match.group("locals"))
        if not isinstance(locals_map, dict):
            continue

        if "ordered_dims" in locals_map:
            ordered_dims = ast.literal_eval(locals_map["ordered_dims"])
            if ordered_dims == ["n", "m"]:
                saw_target_ordered_dims = True
        if "repeat_counts" in locals_map:
            repeat_counts_raw = locals_map["repeat_counts"]
        if "tile_counts" in locals_map:
            tile_counts_raw = locals_map["tile_counts"]
        if "code_list" in locals_map:
            code_list_raw = locals_map["code_list"]

    if not saw_target_ordered_dims or repeat_counts_raw is None or tile_counts_raw is None or code_list_raw is None:
        raise ValueError("Could not find to_index locals for ordered_dims == ['n', 'm'].")

    repeat_counts = _parse_array_of_numbers(repeat_counts_raw)
    tile_counts_vals = _parse_array_of_numbers(tile_counts_raw)
    tile_counts = [int(x) for x in tile_counts_vals]
    code_list = _parse_list_of_arrays(code_list_raw)
    names = ["n", "grp", "rank"]

    return {
        "repeat_counts": repeat_counts,
        "tile_counts": tile_counts,
        "code_list": code_list,
        "names": names,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/coordinates_to_index_loop_state_hard/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/coordinates_to_index_loop_state_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_loop_state(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `xarray/tests/qa/coordinates_to_index_loop_state_hard_test.py`, class "
            "`TestCoordinatesToIndexLoopStateHardQA`, method "
            "`test_coordinates_to_index_loop_state_hard_case`. "
            "At line 23, `ds.coords.to_index(ordered_dims=['n', 'm'])` is called, "
            "which executes `xarray/core/coordinates.py::AbstractCoordinates.to_index`. "
            "In that function, focus on the final state immediately before the return at line 185, "
            "after the loop `for i, index in enumerate(indexes):` has completed. "
            "What are the exact values of `repeat_counts`, `tile_counts`, `code_list`, and `names` "
            "at that point?"
        ),
        "template_answer": {
            "repeat_counts": "list[float]",
            "tile_counts": "list[int]",
            "code_list": "list[list[int]]",
            "names": "list[str]",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
