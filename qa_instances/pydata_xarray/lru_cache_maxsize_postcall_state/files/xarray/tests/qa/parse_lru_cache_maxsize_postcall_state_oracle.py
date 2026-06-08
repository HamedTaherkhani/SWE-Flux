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
    r"(?P<func>[^ ]+) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _parse_test_state(trace_text: str) -> dict[str, object]:
    matches = []
    for m in RETURN_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        func = m.group("func")
        if not path.endswith("/xarray/tests/qa/lru_cache_maxsize_postcall_state_test.py"):
            continue
        if not func.endswith(".test_lru_cache_maxsize_postcall_state_case"):
            continue
        matches.append(m)
    if not matches:
        raise ValueError("Could not find target test return event in trace log.")

    locals_text = matches[-1].group("locals")
    locals_map = ast.literal_eval(locals_text)
    if not isinstance(locals_map, dict):
        raise ValueError("Parsed locals map is not a dict.")

    required = {"post_resize_items", "post_resize_capacity", "post_resize_length"}
    missing = required - set(locals_map)
    if missing:
        raise ValueError(f"Missing expected locals in trace: {sorted(missing)}")

    items = ast.literal_eval(locals_map["post_resize_items"])
    capacity = ast.literal_eval(locals_map["post_resize_capacity"])
    length = ast.literal_eval(locals_map["post_resize_length"])

    if not isinstance(items, list) or not all(
        isinstance(pair, tuple)
        and len(pair) == 2
        and isinstance(pair[0], str)
        and isinstance(pair[1], int)
        for pair in items
    ):
        raise ValueError("post_resize_items is not a list of (str, int) tuples.")
    if not isinstance(capacity, int):
        raise ValueError("post_resize_capacity is not an int.")
    if not isinstance(length, int):
        raise ValueError("post_resize_length is not an int.")

    return {
        "cache_items_in_order": items,
        "cache_maxsize": capacity,
        "cache_length": length,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/lru_cache_maxsize_postcall_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/lru_cache_maxsize_postcall_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = _parse_test_state(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `xarray/tests/qa/lru_cache_maxsize_postcall_state_test.py`, class "
            "`TestLruCacheMaxsizePostcallStateHardQA`, method "
            "`test_lru_cache_maxsize_postcall_state_case`. "
            "In that method, the object `cache` is an instance of "
            "`xarray/backends/lru_cache.py::LRUCache`, and line 18 executes "
            "`cache.maxsize = 2`, which enters the `maxsize` setter "
            "(`xarray/backends/lru_cache.py:98`) and triggers `_enforce_size_limit` "
            "(`xarray/backends/lru_cache.py:60`). Immediately after this setter call, "
            "what are the exact states of `cache._cache` (from oldest to newest item) "
            "and `cache._maxsize`? Return them as `cache_items_in_order` and "
            "`cache_maxsize`. Also return `cache_length`."
        ),
        "template_answer": {
            "cache_items_in_order": "list[tuple[str, int]]",
            "cache_maxsize": "int",
            "cache_length": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
