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

TARGET_FUNCS = {
    "xarray.core.indexes.PandasIndex.sel",
    "xarray.core.indexes.normalize_label",
    "xarray.core.indexes.as_scalar",
    "xarray.core.indexes.get_indexer_nd",
}


def extract_call_order(trace_text: str) -> dict[str, list[str]]:
    order = []
    for m in CALL_RE.finditer(trace_text):
        func = m.group("func")
        if any(func.endswith(f".{name}") for name in ("sel", "normalize_label", "as_scalar", "get_indexer_nd")):
            order.append(func)

    if not order:
        raise ValueError("Could not find target function calls in trace log.")

    return {"function_call_order": order}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/pandasindex_sel_function_call_order_hard/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/pandasindex_sel_function_call_order_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_order(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `xarray/tests/qa/pandasindex_sel_function_call_order_hard_test.py`, class "
            "`TestPandasIndexSelFunctionCallOrderHardQA`, method "
            "`test_pandasindex_sel_function_call_order_hard_case`. "
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
