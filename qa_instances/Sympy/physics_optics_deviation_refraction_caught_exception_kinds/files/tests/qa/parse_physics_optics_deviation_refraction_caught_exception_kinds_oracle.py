#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/sympy/physics/optics/utils\.py:(?P<lineno>\d+) "
    r"(?P<func>sympy\.physics\.optics\.utils\.refraction_angle) "
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
        raise ValueError("Could not find exception events for refraction_angle in trace log.")

    return {"caught_exception_kinds": seen}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/physics_optics_deviation_refraction_caught_exception_kinds/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/physics_optics_deviation_refraction_caught_exception_kinds/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S5_Exceptions",
        "question": (
            "Use `tests/qa/physics_optics_deviation_refraction_caught_exception_kinds_test.py`, class "
            "`TestPhysicsOpticsDeviationRefractionCaughtExceptionKindsQA`, method "
            "`test_physics_optics_deviation_refraction_caught_exception_kinds_case`. "
            "In that test, line 15 and line 16 call `deviation(...)`, which indirectly calls "
            "`sympy/physics/optics/utils.py::refraction_angle` at line 55 via the call on "
            "`deviation` lines 343-347. "
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
