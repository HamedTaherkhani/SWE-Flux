#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/sympy/solvers/solvers\.py:(?P<lineno>\d+) "
    r"(?P<func>sympy\.solvers\.solvers\._solve_system) "
    r"event=exception exc=(?P<exc>[^:]+): ",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    seen = []
    for m in EXC_RE.finditer(trace_text):
        kind = m.group("exc").strip()
        if kind not in seen:
            seen.append(kind)

    if not seen:
        raise ValueError("Could not find exception events for _solve_system in trace log.")

    return {"caught_exception_kinds": seen}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/solvers_solve_caught_exception_kinds/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/solvers_solve_caught_exception_kinds/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S5_Exceptions",
        "question": (
            "Use `tests/qa/solvers_solve_caught_exception_kinds_test.py`, class "
            "`TestSolversSolveCaughtExceptionKindsQA`, method "
            "`test_solvers_solve_caught_exception_kinds_case`. "
            "The loop at lines 14-18 calls `solve(equations, *variables, dict=True)` twice with different systems. "
            "This indirectly enters `sympy/solvers/solvers.py::_solve_system` (defined at line 1757), "
            "which contains internal exception-handling paths while processing those systems. "
            "What are the exact kinds of exceptions that are caught internally during this test execution, in first-seen order?"
        ),
        "template_answer": {
            "caught_exception_kinds": ["str"]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
