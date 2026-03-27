#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

from sympy import Rational, sympify

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/stats/frv\.py):(?P<lineno>\d+) "
    r"(?P<func>sympy\.stats\.frv\.compute_cdf) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _serialize_prob(prob) -> dict:
    if isinstance(prob, Rational):
        return {"num": int(prob.p), "den": int(prob.q)}
    return {"num": int(prob), "den": 1}


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find frv.compute_cdf return events in trace log.")

    parsed_locals = None
    for m in reversed(matches):
        candidate = ast.literal_eval(m.group("locals"))
        if "cdf" in candidate:
            parsed_locals = candidate
            break
    if parsed_locals is None:
        raise ValueError("Could not find local variable `cdf` in frv.compute_cdf trace locals.")

    cdf_pairs = sympify(parsed_locals["cdf"])

    serialized = []
    for key, prob in cdf_pairs:
        serialized.append({
            "value": int(key),
            "cum_prob": _serialize_prob(prob),
        })

    return {"cdf": serialized}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/stats_cdf_indirect_finite_loop_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/stats_cdf_indirect_finite_loop_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/stats_cdf_indirect_finite_loop_state_test.py`, class "
            "`TestStatsCdfIndirectFiniteLoopStateQA`, method "
            "`test_stats_cdf_indirect_finite_loop_state_case`. "
            "In that test, line 10 calls `cdf(transformed)` where `transformed = x**3 - 4*x + 7` "
            "is defined at line 9 from `x = Binomial(\"x\", 20, Rational(2, 5))` on line 7. "
            "During this indirect execution, control reaches `sympy/stats/frv.py::compute_cdf` "
            "(defined at line 272). Inside this function, line 275 initializes `cdf = []` and "
            "the loop at lines 276-279 appends `(key, cum_prob)` pairs. "
            "What exact final value does local variable `cdf` hold at line 279 for this run?"
        ),
        "template_answer": {
            "cdf": [
                {
                    "value": "int",
                    "cum_prob": {"num": "int", "den": "int"}
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
