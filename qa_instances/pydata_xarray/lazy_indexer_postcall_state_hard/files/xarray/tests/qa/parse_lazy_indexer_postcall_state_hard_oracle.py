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

SLICE_RE = re.compile(r"slice\(([^,]+), ([^,]+), ([^)]+)\)")


def _parse_piece(text: str):
    text = text.strip()
    if text == "None":
        return None
    return int(text)


def _parse_slices_tuple_repr(raw: str) -> list[dict[str, int | None]]:
    matches = SLICE_RE.findall(raw)
    if not matches:
        raise ValueError(f"Could not parse slice tuple repr: {raw!r}")

    out = []
    for start, stop, step in matches:
        out.append(
            {
                "start": _parse_piece(start),
                "stop": _parse_piece(stop),
                "step": _parse_piece(step),
            }
        )
    return out


def extract_state(trace_text: str) -> dict[str, object]:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find _updated_key line events in trace log.")

    saw_target_new_key = False
    for match in matches:
        func = match.group("func")
        if not func.endswith("._updated_key"):
            continue

        locals_map = ast.literal_eval(match.group("locals"))
        if not isinstance(locals_map, dict):
            continue

        if "new_key" in locals_map and "slice(1, 3, None)" in locals_map["new_key"]:
            saw_target_new_key = True
        if "full_key_tuple" not in locals_map:
            continue
        if not saw_target_new_key:
            continue

        slices = _parse_slices_tuple_repr(locals_map["full_key_tuple"])
        if len(slices) != 2:
            raise ValueError("Expected exactly two slices in full_key_tuple.")

        return {"full_key_tuple_slices": slices}

    raise ValueError("Could not find full_key_tuple state after expected new_key.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/lazy_indexer_postcall_state_hard/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/lazy_indexer_postcall_state_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_state(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `xarray/tests/qa/lazy_indexer_postcall_state_hard_test.py`, class "
            "`TestLazyIndexerPostcallStateHardQA`, method "
            "`test_lazy_indexer_postcall_state_hard_case`. "
            "At line 16, `lazy[BasicIndexer((slice(1, 3), slice(2, 5, 2)))]` is executed, "
            "which calls `xarray/core/indexing.py::LazilyIndexedArray.__getitem__` and then "
            "`LazilyIndexedArray._updated_key` (line 627). "
            "Inside `_updated_key`, line 634 calls `_index_indexer_1d(...)` within the loop and "
            "appends results to `full_key`. "
            "What is the exact state of `full_key_tuple` immediately after those helper calls are done, "
            "at line 637, for this execution? Return it as `full_key_tuple_slices` as a list of two "
            "objects with keys `start`, `stop`, and `step` in order."
        ),
        "template_answer": {
            "full_key_tuple_slices": [
                {"start": "int|null", "stop": "int|null", "step": "int|null"}
            ]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
