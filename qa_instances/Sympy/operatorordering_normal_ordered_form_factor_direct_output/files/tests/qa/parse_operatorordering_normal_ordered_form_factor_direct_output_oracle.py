#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/physics/quantum/operatorordering\.py):(?P<lineno>\d+) "
    r"(?P<func>sympy\.physics\.quantum\.operatorordering\._normal_ordered_form_factor) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find _normal_ordered_form_factor return events in trace log.")

    target = matches[-1]
    retval = target.group("retval").strip()

    return {
        "output": retval,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/operatorordering_normal_ordered_form_factor_direct_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/operatorordering_normal_ordered_form_factor_direct_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/operatorordering_normal_ordered_form_factor_direct_output_test.py`, class "
            "`TestOperatorOrderingNormalOrderedFormFactorDirectOutputQA`, method "
            "`test_operatorordering_normal_ordered_form_factor_direct_output_case`. "
            "The test directly calls `sympy/physics/quantum/operatorordering.py::_normal_ordered_form_factor` "
            "at lines 20-24 with an operator product constructed at lines 12-18. "
            "Inside `_normal_ordered_form_factor` (defined at line 38), execution performs recursive normal-ordering "
            "and returns an expression from the final return event. "
            "What exact expression string is returned by that final `_normal_ordered_form_factor` return event?"
        ),
        "template_answer": {"output": "str"},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
