#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)

NORMALIZED_FUNCTIONS = {
    "sel": (
        "xarray.core.indexes.PandasIndex.sel|||"
        "xarray/core/indexes.py::PandasIndex.sel|||"
        "xarray.core.indexes.sel|||"
        "xarray/core/indexes.py::sel|||"
        "PandasIndex.sel|||sel"
    ),
    "normalize_label": (
        "xarray.core.indexes.normalize_label|||"
        "xarray/core/indexes.py::normalize_label|||"
        "normalize_label"
    ),
    "as_scalar": (
        "xarray.core.indexes.as_scalar|||"
        "xarray/core/indexes.py::as_scalar|||"
        "as_scalar"
    ),
    "get_indexer_nd": (
        "xarray.core.indexes.get_indexer_nd|||"
        "xarray/core/indexes.py::get_indexer_nd|||"
        "get_indexer_nd"
    ),
}


def _iter_identifier_tokens(func: str) -> list[str]:
    if "|||" in func:
        return [part.strip() for part in func.split("|||") if part.strip()]
    return [func.strip()]


def _short_name(func_token: str) -> str:
    rhs = func_token.split("::", 1)[-1]
    return rhs.rsplit(".", 1)[-1]


def extract_call_order(trace_text: str) -> dict[str, list[str]]:
    order = []
    for m in CALL_RE.finditer(trace_text):
        func = m.group("func")
        matched_key = None
        for token in _iter_identifier_tokens(func):
            short_name = _short_name(token)
            if short_name in NORMALIZED_FUNCTIONS:
                matched_key = short_name
                break
        if matched_key is not None:
            order.append(NORMALIZED_FUNCTIONS[matched_key])

    if not order:
        raise ValueError("Could not find target function calls in trace log.")

    return {"function_call_order": order}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/pandasindex_sel_function_call_order/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/pandasindex_sel_function_call_order/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_order(trace_text)

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `xarray/tests/qa/pandasindex_sel_function_call_order_test.py`, class "
            "`TestPandasIndexSelFunctionCallOrderHardQA`, method "
            "`test_pandasindex_sel_function_call_order_case`. "
            "This test runs two calls to `xarray/core/indexes.py::PandasIndex.sel`: "
            "first with scalar label `{'x': 3}` and second with array label "
            "`{'x': np.array([1, 7], dtype=np.int64)}`, both using "
            "`method='nearest', tolerance=2`. "
            "Considering only calls to these functions in `xarray/core/indexes.py`: "
            "`PandasIndex.sel`, `normalize_label`, `as_scalar`, and `get_indexer_nd`, "
            "what is the exact execution order of function calls during the full test run "
            "(including repeats)?"
        ),
        "template_answer": {
            "function_call_order": ["str"]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
