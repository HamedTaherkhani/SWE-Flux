#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/sympy/logic/algorithms/dpll.py"
TARGET_FUNC = "sympy.logic.algorithms.dpll.dpll_int_repr"
LOOP_BODY_LINE = 128

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/logic/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def count_loop_iterations(trace_text: str) -> int:
    depth = 0
    count = 0

    for line in trace_text.splitlines():
        m = EVENT_RE.match(line)
        if not m:
            continue

        path = m.group("path")
        func = m.group("func")
        event = m.group("event")
        lineno = int(m.group("lineno"))

        if path != TARGET_PATH or func != TARGET_FUNC:
            continue

        if event == "call":
            depth += 1
            continue

        if event in {"return", "exception"}:
            depth = max(0, depth - 1)
            continue

        if event == "line" and depth == 1 and lineno == LOOP_BODY_LINE:
            count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/logic_dpll_unknown_clause_loop_iterations/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/logic_dpll_unknown_clause_loop_iterations/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    iteration_count = count_loop_iterations(trace_text)

    qa = {
        "question_kind": "S2_Loops",
        "question": (
            "Use `tests/qa/logic_dpll_unknown_clause_loop_iterations_test.py`, class "
            "`TestLogicDpllUnknownClauseLoopIterationsQA`, method "
            "`test_logic_dpll_unknown_clause_loop_iterations_case`. "
            "The test calls `satisfiable(expr, algorithm=\"dpll\")` at line 8, which calls "
            "`sympy.logic.algorithms.dpll.dpll_satisfiable` and then "
            "`sympy.logic.algorithms.dpll.dpll_int_repr`. "
            "In file `sympy/logic/algorithms/dpll.py`, function "
            "`sympy.logic.algorithms.dpll.dpll_int_repr`, consider the loop "
            "`for c in clauses:` at line `127` (body starts at line `128`). "
            "How many iterations does this loop execute during this test run in the top-level "
            "invocation of `dpll_int_repr`? Return a JSON object with key "
            "`loop_iteration_count` and integer value."
        ),
        "template_answer": {
            "loop_iteration_count": "int",
        },
        "oracle_answer": {
            "loop_iteration_count": iteration_count,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
