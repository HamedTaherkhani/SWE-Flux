#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/reflex/vars/(?:sequence|object|number|function)\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for execution path extraction.")

    executed_path = []
    for match in matches:
        executed_path.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": match.group("func"),
                "line": int(match.group("lineno")),
            }
        )

    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/vars_array_foreach_execution_path_lines/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/vars_array_foreach_execution_path_lines/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_execution_path(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `tests/qa/vars_array_foreach_execution_path_lines_test.py`, class "
            "`TestVarsArrayForeachExecutionPathLinesQA`, method "
            "`test_vars_array_foreach_execution_path_lines_case`. "
            "At lines 15-17, the test calls `rows.foreach(lambda item: item[\"score\"] + item[\"bonus\"] * 2)` "
            "after constructing `rows` at lines 9-12 with `_js_expr=\"state.rows.filter((row) => row.active)\"` "
            "and `_var_type=list[dict[str, int]]`. "
            "Return the execution path only for line events in files `reflex/vars/sequence.py`, "
            "`reflex/vars/object.py`, `reflex/vars/number.py`, and `reflex/vars/function.py`, and only for these functions: "
            "`reflex.vars.sequence.ArrayVar.foreach`, `reflex.vars.sequence.ArrayVar.__getitem__`, "
            "`reflex.vars.sequence.array_item_operation`, `reflex.vars.object.ObjectVar.__getitem__`, "
            "`reflex.vars.object.ObjectVar.__getattr__`, `reflex.vars.number.NumberVar.__mul__`, "
            "`reflex.vars.number.number_multiply_operation`, `reflex.vars.number.NumberVar.__add__`, "
            "`reflex.vars.number.number_add_operation`, `reflex.vars.function.ArgsFunctionOperation.create`, and "
            "`reflex.vars.sequence.map_array_operation`. "
            "This execution crosses multiple classes and files while resolving the foreach item type, object field access, "
            "numeric operations, lambda wrapping, and final array mapping. "
            "What is the exact ordered execution path as a list of objects with keys `file`, `func`, and `line`, including repeated lines?"
        ),
        "template_answer": {
            "executed_path": [
                {
                    "file": "str",
                    "func": "str",
                    "line": "int",
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
