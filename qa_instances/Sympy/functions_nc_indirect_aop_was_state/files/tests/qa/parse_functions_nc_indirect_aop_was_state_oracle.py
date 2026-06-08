#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/functions/combinatorial/numbers\.py):(?P<lineno>\d+) "
    r"(?P<func>sympy\.functions\.combinatorial\.numbers\._AOP_product) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find _AOP_product return events in trace log.")

    parsed_locals = ast.literal_eval(matches[-1].group("locals"))
    if "was" not in parsed_locals:
        raise ValueError("Could not find local variable `was` in _AOP_product trace locals.")

    was = ast.literal_eval(parsed_locals["was"])
    if not isinstance(was, list):
        raise ValueError(f"Expected `was` to parse into a list, got: {type(was).__name__}")

    return {"was": was}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/functions_nc_indirect_aop_was_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/functions_nc_indirect_aop_was_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/functions_nc_indirect_aop_was_state_test.py`, class "
            "`TestFunctionsNcIndirectAopWasStateQA`, method "
            "`test_functions_nc_indirect_aop_was_state_case`. "
            "In that test, line 9 calls `nC(bag, k)` with `bag` from line 6 and `k` from line 7. "
            "During this indirect execution, control reaches `sympy/functions/combinatorial/numbers.py::_AOP_product` "
            "(defined at line 2452). Inside the `while n:` loop, line 2487 assigns `was = rv[:]`, then lines 2488-2491 update `rv` in two loops. "
            "What exact list value does local variable `was` hold at line 2487 in the final loop iteration for this run?"
        ),
        "template_answer": {"was": ["int"]},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
