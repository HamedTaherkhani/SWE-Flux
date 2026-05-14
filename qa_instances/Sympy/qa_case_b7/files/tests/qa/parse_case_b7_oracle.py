#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/solvers/deutils\.py):(?P<lineno>\d+) "
    r"(?P<func>sympy\.solvers\.deutils\._desolve) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

HINT_RE = re.compile(r"'hint':\s*'(?P<hint>[^']+)'")
ORDER_RE = re.compile(r"'order':\s*(?P<order>\d+)")
FUNC_RE = re.compile(r"'func':\s*(?P<func>[^,}]+)")


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find _desolve return events in trace log.")

    target = None
    for m in matches:
        if m.group("lineno") == "273":
            target = m
    if target is None:
        target = matches[-1]

    retval = target.group("retval")

    hint_match = HINT_RE.search(retval)
    order_match = ORDER_RE.search(retval)
    func_match = FUNC_RE.search(retval)

    if not (hint_match and order_match and func_match):
        raise ValueError("Could not extract hint/order/func from _desolve retval.")

    return {
        "hint": hint_match.group("hint"),
        "order": int(order_match.group("order")),
        "func": func_match.group("func").strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/qa_case_b7/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/qa_case_b7/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `tests/qa/case_b7_test.py`, class `TestCaseB7QA`, method `test_case_b7`. "
            "This test directly calls `sympy/solvers/deutils.py::_desolve` at line 15 with "
            "`hint='default'` and `type='ode'` on the ODE built in lines 10-13. "
            "Inside `_desolve` (defined at line 134), focus on the dictionary return construction path "
            "that reaches line 273 (`return hints`). "
            "What are the exact final values for keys `hint`, `order`, and `func` in that returned dictionary?"
        ),
        "template_answer": {
            "hint": "str",
            "order": "int",
            "func": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
