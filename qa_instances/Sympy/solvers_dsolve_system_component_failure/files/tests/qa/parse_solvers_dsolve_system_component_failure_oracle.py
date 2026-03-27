#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

EXC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/sympy/solvers/ode/systems\.py:(?P<lineno>\d+) "
    r"(?P<func>sympy\.solvers\.ode\.systems\._weak_component_solver) "
    r"event=exception exc=(?P<exc>.*?) locals=\{.*\}$",
    re.MULTILINE,
)


def _decode_exception(exc_blob: str) -> tuple[str, str]:
    if ": " in exc_blob:
        exc_type, rest = exc_blob.split(": ", 1)
    else:
        return exc_blob.strip(), ""

    m = re.match(r"^[A-Za-z_][A-Za-z0-9_]*\((?P<args>.*)\)$", rest)
    if not m:
        return exc_type.strip(), rest.strip()

    args_text = m.group("args").strip()
    if not args_text:
        return exc_type.strip(), ""

    try:
        msg = ast.literal_eval(args_text)
        if isinstance(msg, tuple):
            msg = ", ".join(str(x) for x in msg)
        return exc_type.strip(), str(msg)
    except Exception:
        return exc_type.strip(), rest.strip()


def extract_output(trace_text: str) -> dict:
    matches = list(EXC_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find _weak_component_solver exception events in trace log.")

    exc_blob = matches[-1].group("exc")
    exc_type, exc_message = _decode_exception(exc_blob)
    return {
        "exception_type": exc_type,
        "exception_message": exc_message,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/solvers_dsolve_system_component_failure/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/solvers_dsolve_system_component_failure/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "abnormal_behavior_prediction",
        "question": (
            "Use `tests/qa/solvers_dsolve_system_component_failure_test.py`, class "
            "`TestSolversDsolveSystemComponentFailureQA`, method "
            "`test_solvers_dsolve_system_component_failure_case`. "
            "In that test, line 15 calls `dsolve_system(equations)` for the system built in lines 10-13. "
            "During this call, execution descends through the ODE system decomposition logic in "
            "`sympy/solvers/ode/systems.py`, including `_weak_component_solver` (defined at line 1733). "
            "What uncaught exception is thrown by this run? Provide both the exact exception type and exact exception message."
        ),
        "template_answer": {
            "exception_type": "str",
            "exception_message": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
