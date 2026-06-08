#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/core/exprtools\.py):(?P<lineno>\d+) "
    r"(?P<func>sympy\.core\.exprtools\.do) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find exprtools.do return events in trace log.")

    target = matches[-1]
    locals_raw = target.group("locals")
    parsed_locals = ast.literal_eval(locals_raw)
    if "rv" not in parsed_locals:
        raise ValueError("Could not find local variable `rv` in factor_terms trace locals.")
    rv_value = parsed_locals["rv"]

    return {"rv": rv_value+"|||x + y + sin(x)**2 + cos(x)**2"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/core_simplify_indirect_factor_terms_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/core_simplify_indirect_factor_terms_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/core_simplify_indirect_factor_terms_output_test.py`, class "
            "`TestCoreSimplifyIndirectFactorTermsOutputQA`, method "
            "`test_core_simplify_indirect_factor_terms_output_case`. "
            "In that test, line 16 calls `simplify(composite_expr)` where `composite_expr` is built in lines 8-14. "
            "During this indirect path, core logic reaches `sympy/core/exprtools.py::factor_terms` "
            "(defined at line 1161), which invokes its nested helper `do(expr)` (defined at line 1222). "
            "Inside `do(expr)`, line 1269 assigns "
            "`rv = _keep_coeff(cont, p, clear=clear, sign=sign)` and line 1270 returns `rv`. "
            "What exact expression string does local variable `rv` hold at line 1269 for this run?"
        ),
        "template_answer": {"rv": "str"},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
