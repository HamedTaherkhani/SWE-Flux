#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/reflex/state\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)

ALLOWED_FUNCS = {
    "reflex.state.BaseState.get_delta",
    "reflex.state.BaseState._mark_dirty_computed_vars",
    "reflex.state.BaseState._expired_computed_vars",
    "reflex.state.BaseState._dirty_computed_vars",
    "reflex.state.BaseState.get_value",
}


def extract_call_order(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find call events for function-call order extraction.")

    function_call_order = []
    for match in matches:
        func_name = match.group("func")
        if func_name not in ALLOWED_FUNCS or "<locals>" in func_name:
            continue
        function_call_order.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": func_name,
            }
        )
    if not function_call_order:
        raise ValueError("Trace had call events, but none matched the exact target functions.")
    return {"function_call_order": function_call_order}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/state_delta_function_call_order/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/state_delta_function_call_order/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_order(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `tests/qa/state_delta_function_call_order_test.py`, class "
            "`TestStateDeltaFunctionCallOrderQA`, method `test_state_delta_function_call_order_case`. "
            "The `DeltaOrderState` instance is created at line 14, its `count` and `label` fields are changed "
            "at lines 15-16, and line 18 executes `delta = state.get_delta()`. During this test run, return the exact ordered sequence "
            "of function calls only for file `reflex/state.py` and only for these functions: "
            "`reflex.state.BaseState.get_delta`, `reflex.state.BaseState._mark_dirty_computed_vars`, "
            "`reflex.state.BaseState._expired_computed_vars`, `reflex.state.BaseState._dirty_computed_vars`, and "
            "`reflex.state.BaseState.get_value`. What is the exact ordered sequence of function calls as a list "
            "of objects with keys `file` and `func`, including repeated calls?"
        ),
        "template_answer": {
            "function_call_order": [
                {
                    "file": "str",
                    "func": "str",
                }
            ]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
