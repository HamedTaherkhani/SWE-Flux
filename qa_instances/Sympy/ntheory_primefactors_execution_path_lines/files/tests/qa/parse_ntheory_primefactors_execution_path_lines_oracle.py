#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/ntheory/factor_\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for execution path extraction.")

    executed_path = []
    for match in matches:
        executed_path.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": match.group("func"),
                "line": int(match.group("lineno")),
            }
        )

    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/ntheory_primefactors_execution_path_lines/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/ntheory_primefactors_execution_path_lines/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_execution_path(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `tests/qa/ntheory_primefactors_execution_path_lines_test.py`, class "
            "`TestNTheoryPrimefactorsExecutionPathLinesQA`, method "
            "`test_ntheory_primefactors_execution_path_lines_case`. "
            "At lines 9-15, the test calls `primefactors(value, limit=100500, use_rho=False, use_pm1=False, use_ecm=False)`. "
            "Return the execution path only for events in file `sympy/ntheory/factor_.py` and only for these functions: "
            "`sympy.ntheory.factor_.primefactors`, `sympy.ntheory.factor_.factorint`, and "
            "`sympy.ntheory.factor_._factorint_small`. "
            "This execution has multiple loops and repeated branches. "
            "What is the exact ordered execution path as a list of objects with keys `file`, `func`, and `line`, including repeated lines?"
        ),
        "template_answer": {
            "executed_path": [
                {
                    "file": "str",
                    "func": "str",
                    "line": "int",
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
