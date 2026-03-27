#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/matrices/expressions/blockmatrix\.py):(?P<lineno>\d+) "
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
        default="/testbed/logs/qa_instances/matrices_blockmatrix_function_call_order/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/matrices_blockmatrix_function_call_order/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_order(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `tests/qa/matrices_blockmatrix_function_call_order_test.py`, class "
            "`TestMatricesBlockmatrixFunctionCallOrderQA`, method "
            "`test_matrices_blockmatrix_function_call_order_case`. "
            "At line 19, `collapsed = block_collapse(expr)` is executed. "
            "Return the exact ordered sequence of function calls only for file "
            "`sympy/matrices/expressions/blockmatrix.py` and only for these functions: "
            "`sympy.matrices.expressions.blockmatrix.block_collapse`, "
            "`sympy.matrices.expressions.blockmatrix.bc_unpack`, "
            "`sympy.matrices.expressions.blockmatrix.bc_matadd`, "
            "`sympy.matrices.expressions.blockmatrix.bc_block_plus_ident`, "
            "`sympy.matrices.expressions.blockmatrix.bc_dist`, "
            "`sympy.matrices.expressions.blockmatrix.bc_matmul`, "
            "`sympy.matrices.expressions.blockmatrix.bc_transpose`, "
            "`sympy.matrices.expressions.blockmatrix.bc_inverse`, "
            "`sympy.matrices.expressions.blockmatrix.blockinverse_1x1`, "
            "`sympy.matrices.expressions.blockmatrix.blockinverse_2x2`, "
            "`sympy.matrices.expressions.blockmatrix._choose_2x2_inversion_formula`, "
            "`sympy.matrices.expressions.blockmatrix.deblock`, and "
            "`sympy.matrices.expressions.blockmatrix.reblock_2x2`. "
            "What is the exact ordered sequence of function calls as a list of objects with keys "
            "`file` and `func`, including repeated calls?"
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
