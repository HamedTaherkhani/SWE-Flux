#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_FUNC = "sympy.strategies.branch.traverse.sall"
CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/strategies/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)


def extract_call_frequency(trace_text: str) -> dict:
    call_count = 0
    for match in CALL_RE.finditer(trace_text):
        if match.group("func") == TARGET_FUNC:
            call_count += 1
    return {"function_call_count": call_count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/strategies_branch_sall_call_frequency/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/strategies_branch_sall_call_frequency/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_frequency(trace_text)

    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/strategies_branch_sall_call_frequency_test.py`, class "
            "`TestStrategiesBranchSallCallFrequencyQA`, method "
            "`test_strategies_branch_sall_call_frequency_case`. "
            "At line 16, `results = tuple(canonical_rule(expr_tree))` is executed. "
            "During this test run, how many times is function "
            "`sympy.strategies.branch.traverse.sall` in file "
            "`sympy/strategies/branch/traverse.py` called?"
        ),
        "template_answer": {
            "function_call_count": "int"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
