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


def _parse_1d_array_repr(array_repr: str) -> list[int]:
    m = ARRAY_RE.search(array_repr)
    if m is None:
        raise ValueError(f"Could not parse array repr: {array_repr!r}")
    raw = m.group(1)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [int(p) for p in parts]


def _parse_dim_pos_indexers_repr(text: str) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for key in ("x", "y"):
        m = re.search(rf"'{key}'\s*:\s*(array\(\[[^\]]*\]\))", text)
        if m is None:
            raise ValueError(f"Could not find key {key!r} in dim_pos_indexers repr.")
        result[key] = _parse_1d_array_repr(m.group(1))
    return result


def extract_input_state(trace_text: str) -> dict[str, object]:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find reindex_variables line events in trace log.")

    latest_dim_pos_indexers = None
    latest_fill_value = None
    for match in matches:
        func = match.group("func")
        if not func.endswith(".reindex_variables"):
            continue

        locals_map = ast.literal_eval(match.group("locals"))
        if not isinstance(locals_map, dict):
            continue

        if "dim_pos_indexers" in locals_map:
            latest_dim_pos_indexers = _parse_dim_pos_indexers_repr(locals_map["dim_pos_indexers"])
        if "fill_value" in locals_map:
            latest_fill_value = ast.literal_eval(locals_map["fill_value"])

        if "dim" not in locals_map or "indxr" not in locals_map:
            continue

        dim_value = ast.literal_eval(locals_map["dim"])
        if dim_value != "y":
            continue

        if latest_dim_pos_indexers is None or latest_fill_value is None:
            continue

        current_indxr = _parse_1d_array_repr(locals_map["indxr"])
        fill_value = latest_fill_value

        if not isinstance(fill_value, dict):
            raise ValueError("fill_value is not a dict.")

        return {
            "dim_pos_indexers": latest_dim_pos_indexers,
            "current_dim": dim_value,
            "current_indxr": current_indxr,
            "fill_value": fill_value,
        }

    raise ValueError("Could not find target line-59 event for dim == 'y'.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/reindex_variables_input_state_indirect/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/reindex_variables_input_state_indirect/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_input_state(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `xarray/tests/qa/reindex_variables_input_state_indirect_test.py`, class "
            "`TestReindexVariablesInputStateIndirectHardQA`, method "
            "`test_reindex_variables_input_state_indirect_case`. "
            "At line 30, the test calls `Dataset.reindex(...)`, which indirectly invokes "
            "`xarray/core/alignment.py::reindex_variables` at line 38. "
            "Inside `reindex_variables`, focus on line 59 (`if (indxr < 0).any():`) during the "
            "iteration where `dim == 'y'`. "
            "What are the exact states of input mapping `dim_pos_indexers`, current loop indexer "
            "`indxr`, and `fill_value` at that point? Return JSON with keys "
            "`dim_pos_indexers`, `current_dim`, `current_indxr`, and `fill_value`."
        ),
        "template_answer": {
            "dim_pos_indexers": "dict[str, list[int]]",
            "current_dim": "str",
            "current_indxr": "list[int]",
            "fill_value": "dict[str, object]",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
