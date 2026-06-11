#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from sympy import sympify
from sympy.core.basic import Basic
from sympy.core.numbers import Integer

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/core/mul\.py):(?P<lineno>\d+) "
    r"(?P<func>sympy\.core\.mul\.flatten) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _to_jsonable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Integer):
        return int(value)
    if isinstance(value, Basic):
        return str(value)
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return str(value)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find sympy.core.mul.flatten return events in trace log.")

    target = matches[-1]
    locals_raw = target.group("locals")
    parsed_locals = ast.literal_eval(locals_raw)

    if not all(k in parsed_locals for k in ("c_part", "nc_part", "order_symbols")):
        raise ValueError("Final flatten return event does not include c_part/nc_part/order_symbols in locals.")

    c_part = sympify(parsed_locals["c_part"])
    nc_part = sympify(parsed_locals["nc_part"])
    order_symbols = sympify(parsed_locals["order_symbols"])

    return {
        "c_part": _to_jsonable(c_part),
        "nc_part": _to_jsonable(nc_part),
        "order_symbols": _to_jsonable(order_symbols),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/core_expand_mul_indirect_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/core_expand_mul_indirect_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/core_expand_mul_indirect_output_test.py`, class "
            "`TestCoreExpandMulIndirectOutputQA`, method "
            "`test_core_expand_mul_indirect_output_case`. "
            "In that test, line 6 defines `x, y, z`, line 7 builds "
            "`composite_expr = (x + 2*y - z)**3 * (x - y + z/2)`, and "
            "lines 9-14 call `expand(composite_expr, mul=True, power_exp=True, power_base=True)`. "
            "During this indirect path, `sympy/core/mul.py::flatten` "
            "(defined at line 206) executes and reaches the return statement "
            "at `sympy/core/mul.py:735` (`return c_part, nc_part, order_symbols`). "
            "What are the exact final values returned at that line for "
            "`c_part`, `nc_part`, and `order_symbols`?"
        ),
        "template_answer": {
            "c_part": ["int | str"],
            "nc_part": ["int | str"],
            "order_symbols": "null | list",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
