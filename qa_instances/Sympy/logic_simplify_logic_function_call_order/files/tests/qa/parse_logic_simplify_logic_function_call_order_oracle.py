#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/logic/boolalg\.py):(?P<lineno>\d+) "
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
        default="/testbed/logs/qa_instances/logic_simplify_logic_function_call_order/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/logic_simplify_logic_function_call_order/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_order(trace_text)

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/logic_simplify_logic_function_call_order_test.py`, class "
            "`TestLogicSimplifyLogicFunctionCallOrderQA`, method "
            "`test_logic_simplify_logic_function_call_order_case`. "
            "At line 20, `simplify_logic(expr, form=\"dnf\", deep=True, force=True)` is executed. "
            "Return the exact ordered sequence of function calls only for file `sympy/logic/boolalg.py` "
            "and only for these functions: `sympy.logic.boolalg.simplify_logic`, "
            "`sympy.logic.boolalg._find_predicates`, `sympy.logic.boolalg._get_truthtable`, "
            "`sympy.logic.boolalg._finger`, `sympy.logic.boolalg.SOPform`, "
            "`sympy.logic.boolalg._sop_form`, `sympy.logic.boolalg._input_to_binlist`, "
            "`sympy.logic.boolalg._simplified_pairs`, `sympy.logic.boolalg._check_pair`, "
            "`sympy.logic.boolalg._rem_redundancy`, and `sympy.logic.boolalg._convert_to_varsSOP`. "
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
