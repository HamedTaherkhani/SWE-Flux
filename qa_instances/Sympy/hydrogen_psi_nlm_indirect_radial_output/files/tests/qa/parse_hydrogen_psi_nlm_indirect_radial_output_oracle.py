#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/physics/hydrogen\.py):(?P<lineno>\d+) "
    r"(?P<func>sympy\.physics\.hydrogen\.R_nl) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find R_nl return events in trace log.")

    target = matches[-1]
    retval = target.group("retval").strip()

    return {"output": retval}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/hydrogen_psi_nlm_indirect_radial_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/hydrogen_psi_nlm_indirect_radial_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `tests/qa/hydrogen_psi_nlm_indirect_radial_output_test.py`, class "
            "`TestHydrogenPsiNlmIndirectRadialOutputQA`, method "
            "`test_hydrogen_psi_nlm_indirect_radial_output_case`. "
            "In that test, line 13 calls `Psi_nlm(7, 3, 1, r, phi, theta, Z)` from "
            "`sympy/physics/hydrogen.py`. "
            "During this indirect path, `Psi_nlm` (defined at line 95) calls "
            "`R_nl` (defined at line 10), and `R_nl` returns at line 92. "
            "What exact expression string is returned by the final `R_nl` return event?"
        ),
        "template_answer": {"output": "str"},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
