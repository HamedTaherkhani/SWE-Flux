#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/sympy/ntheory/factor_.py"
TARGET_FUNC = "sympy.ntheory.factor_.factorint"
LOOP_ITER_MARK_LINE = 1529
TARGET_VALUE_LINE = 1530
NTH = 2
VARIABLE = "fermat"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/ntheory/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _parse_locals(line: str) -> dict[str, str]:
    idx = line.find(" locals=")
    if idx == -1:
        return {}
    raw = line[idx + len(" locals="):].strip()
    try:
        value = ast.literal_eval(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _decode_value(raw: str):
    try:
        return ast.literal_eval(raw)
    except Exception:
        return raw


def extract_nth_iteration_value(trace_text: str) -> dict[str, object]:
    depth = 0
    iteration = 0
    current_iteration = 0

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

        if event == "line" and depth == 1 and lineno == LOOP_ITER_MARK_LINE:
            iteration += 1
            current_iteration = iteration
            continue

        if (
            event == "line"
            and depth == 1
            and lineno == TARGET_VALUE_LINE
            and current_iteration == NTH
        ):
            locals_map = _parse_locals(line)
            if VARIABLE not in locals_map:
                raise ValueError(
                    f"Variable '{VARIABLE}' missing at iteration {NTH} on line {TARGET_VALUE_LINE}."
                )
            return {
                "nth_iteration": NTH,
                "variable": VARIABLE,
                "value": _decode_value(locals_map[VARIABLE]),
            }

    raise ValueError(f"Could not observe iteration {NTH} in top-level target loop.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/ntheory_factorint_fermat_nth_iteration_value/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/ntheory_factorint_fermat_nth_iteration_value/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_nth_iteration_value(trace_text)

    qa = {
        "question_kind": "S3_Loops",
        "question": (
            "Use `tests/qa/ntheory_factorint_fermat_nth_iteration_value_test.py`, class "
            "`TestNTheoryFactorintFermatNthIterationValueQA`, method "
            "`test_ntheory_factorint_fermat_nth_iteration_value_case`. "
            "The test calls `primefactors(10000029966999901)` at line 6, which calls "
            "`sympy.ntheory.factor_.factorint`. "
            "In file `sympy/ntheory/factor_.py`, function `sympy.ntheory.factor_.factorint`, "
            "consider the loop `for _ in range(3):` at line `1528`. "
            "For the 2nd iteration of that loop in the top-level invocation, after executing "
            "line `1530` (`b, fermat = sqrtrem(b2)`), what is the exact value of variable "
            "`fermat`? "
            "Return a JSON object with exactly keys: `nth_iteration`, `variable`, `value`."
        ),
        "template_answer": {
            "nth_iteration": "int",
            "variable": "str",
            "value": "int",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
