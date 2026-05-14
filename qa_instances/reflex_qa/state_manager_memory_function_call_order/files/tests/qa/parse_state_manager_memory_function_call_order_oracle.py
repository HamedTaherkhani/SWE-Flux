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
    "reflex.state.StateManagerMemory.modify_state",
    "reflex.state.StateManagerMemory.get_state",
    "reflex.state.StateManagerMemory.set_state",
    "reflex.state._split_substate_key",
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
        default="/testbed/logs/qa_instances/state_manager_memory_function_call_order/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/state_manager_memory_function_call_order/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_order(trace_text)

    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/state_manager_memory_function_call_order_test.py`, class "
            "`TestStateManagerMemoryFunctionCallOrderQA`, method "
            "`test_state_manager_memory_function_call_order_case`. The `StateManagerMemory` instance is created "
            "at line 15, its in-memory stores are reset at lines 16-17, lines 19-20 execute "
            "`async with manager.modify_state(\"client-token_child\") as state`, line 22 executes "
            "`same_state = await manager.get_state(\"client-token_other\")`, and line 23 executes "
            "`await manager.set_state(\"client-token\", same_state)`. Return the exact ordered sequence of "
            "function calls only for file `reflex/state.py` and only for these functions: "
            "`reflex.state.StateManagerMemory.modify_state`, `reflex.state.StateManagerMemory.get_state`, "
            "`reflex.state.StateManagerMemory.set_state`, and `reflex.state._split_substate_key`. "
            "What is the exact ordered sequence of function calls as a list of objects with keys `file` and "
            "`func`, including repeated calls?"
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
