#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/solvers/deutils\.py):(?P<lineno>\d+) "
    r"(?P<func>sympy\.solvers\.deutils\.ode_order) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find ode_order return events in trace log.")

    target = matches[-1]
    retval = target.group("retval").strip()
    parsed = ast.literal_eval(retval)
    if not isinstance(parsed, int):
        raise ValueError("Expected ode_order retval to be an integer.")

    return {"order": parsed}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/dsolve_classify_ode_indirect_hints/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/dsolve_classify_ode_indirect_hints/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/dsolve_classify_ode_indirect_hints_test.py`, class "
            "`TestDsolveClassifyOdeIndirectHintsQA`, method "
            "`test_dsolve_classify_ode_indirect_hints_case`. "
            "In that test, line 9 constructs the second-order ODE expression (`ode_expr`) and "
            "line 14 calls `dsolve(ode_expr)`. "
            "During this indirect nested solver path, `sympy/solvers/ode/ode.py::classify_ode` "
            "calls `sympy/solvers/deutils.py::ode_order` (defined at line 94). "
            "For the final `ode_order` return event at line 131 "
            "(`return max(ode_order(_, func) for _ in expr.args) if expr.args else 0`), "
            "what exact integer order is returned?"
        ),
        "template_answer": {"order": "int"},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
