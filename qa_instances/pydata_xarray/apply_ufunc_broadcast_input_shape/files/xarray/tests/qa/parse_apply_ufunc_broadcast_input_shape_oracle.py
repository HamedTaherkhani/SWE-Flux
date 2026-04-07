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

def extract_shape(trace_text: str) -> dict[str, object]:
    matches = []
    for m in RETURN_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        func = m.group("func")
        if not path.endswith("/xarray/tests/qa/apply_ufunc_broadcast_input_shape_test.py"):
            continue
        if not func.endswith(".test_apply_ufunc_broadcast_input_shape_case"):
            continue
        matches.append(m)
    if not matches:
        raise ValueError("Could not find target test return event in trace log.")

    locals_map = ast.literal_eval(matches[-1].group("locals"))
    if "observed_data_shape" not in locals_map:
        raise ValueError("Missing observed_data_shape in test locals.")
    data_shape = ast.literal_eval(locals_map["observed_data_shape"])
    if not isinstance(data_shape, list) or not all(isinstance(x, int) for x in data_shape):
        raise ValueError("observed_data_shape is not list[int].")
    return {"data_shape": data_shape}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/apply_ufunc_broadcast_input_shape/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/apply_ufunc_broadcast_input_shape/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_shape(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `xarray/tests/qa/apply_ufunc_broadcast_input_shape_test.py`, class "
            "`TestApplyUfuncBroadcastInputShapeHardQA`, method "
            "`test_apply_ufunc_broadcast_input_shape_case`. "
            "At line 28, `xr.apply_ufunc(...)` is called with two inputs and "
            "`input_core_dims=[['y'], ['y']]`. After this call returns, what is the exact "
            "shape of `out.data` in this test execution?"
        ),
        "template_answer": {
            "data_shape": "list[int]"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
