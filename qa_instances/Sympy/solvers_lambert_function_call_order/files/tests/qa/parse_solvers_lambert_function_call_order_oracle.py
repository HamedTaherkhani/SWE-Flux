#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/solvers/solvers\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)


def extract_call_order(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find call events for function-call order extraction.")

    function_call_order = []
    for match in matches:
        func_name = match.group("func")
        if "<locals>" in func_name:
            continue

        function_call_order.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": func_name,
            }
        )

    return {"function_call_order": function_call_order}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/solvers_lambert_function_call_order/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/solvers_lambert_function_call_order/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_order(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `tests/qa/solvers_lambert_function_call_order_test.py`, class "
            "`TestSolversLambertFunctionCallOrderQA`, method "
            "`test_solvers_lambert_function_call_order_case`. "
            "At lines 9-12, the test performs two calls to `solve(..., dict=True)` for exponential equations. "
            "Return the exact ordered sequence of function calls only for file `sympy/solvers/solvers.py` "
            "and only for these functions: `sympy.solvers.solvers.solve`, "
            "`sympy.solvers.solvers._sympified_list`, `sympy.solvers.solvers.recast_to_symbols`, "
            "`sympy.solvers.solvers._solve`, `sympy.solvers.solvers._vsolve`, "
            "`sympy.solvers.solvers._tsolve`, `sympy.solvers.solvers._invert`, "
            "`sympy.solvers.solvers._ispow`, `sympy.solvers.solvers._as_base_q`, "
            "`sympy.solvers.solvers.solve_linear`, `sympy.solvers.solvers.unrad`, "
            "`sympy.solvers.solvers.denoms`, `sympy.solvers.solvers._simple_dens`, "
            "`sympy.solvers.solvers._take`, and `sympy.solvers.solvers._has_piecewise`. "
            "What is the exact ordered sequence of function calls as a list of objects with keys `file` and `func`, including repeated calls?"
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
