#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/reflex/(?:state|event)\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)

ALLOWED_FUNCS = {
    "reflex.state.BaseState._process_event",
    "reflex.state.BaseState._as_state_update",
    "reflex.event.fix_events",
    "reflex.event.EventHandler.__call__",
}


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for execution path extraction.")

    executed_path = []
    for match in matches:
        func = match.group("func")
        if func not in ALLOWED_FUNCS:
            continue
        executed_path.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": func,
                "line": int(match.group("lineno")),
            }
        )
    if not executed_path:
        raise ValueError("Trace had line events, but none matched the exact target functions.")
    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/state_generator_process_event_execution_path_lines/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/state_generator_process_event_execution_path_lines/oracle.json",
    )
    args = parser.parse_args()

    output = extract_execution_path(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `tests/qa/state_generator_process_event_execution_path_lines_test.py`, class "
            "`TestStateGeneratorProcessEventExecutionPathLinesQA`, method "
            "`test_state_generator_process_event_execution_path_lines_case`. "
            "At lines 78-82, the test iterates over `state._process_event(handler=handler, state=state, payload=payload)` "
            "using the payload built at lines 70-75 and the handler selected at line 69. Return the execution path only "
            "for line events in files `reflex/state.py` and `reflex/event.py`, and only for these functions: "
            "`reflex.state.BaseState._process_event`, `reflex.state.BaseState._as_state_update`, "
            "`reflex.event.fix_events`, and `reflex.event.EventHandler.__call__`. "
            "This execution coerces payload types, drives a generator handler through two yields and a return value, "
            "and converts yielded handlers/specs into frontend events. What is the exact ordered execution path as a "
            "list of objects with keys `file`, `func`, and `line`, including repeated lines?"
        ),
        "template_answer": {
            "executed_path": [{"file": "str", "func": "str", "line": "int"}]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
