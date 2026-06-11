#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/sympy/utilities/lambdify.py"
TARGET_FUNC = "sympy.utilities.lambdify.lambdify"

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/sympy/utilities/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=return retval=(?P<retval>.+?) locals=\{"
)


def extract_retvals(trace_text: str) -> list[str]:
    retvals: list[str] = []
    for raw_line in trace_text.splitlines():
        m = RETURN_RE.match(raw_line)
        if not m:
            continue
        if m.group("path") != TARGET_PATH:
            continue
        if m.group("func") != TARGET_FUNC:
            continue
        retvals.append(m.group("retval"))
    return retvals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "utilities_lambdify_generated_function_output_determinism/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "utilities_lambdify_generated_function_output_determinism/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    retvals = extract_retvals(trace_text)

    invariant_exists = len(retvals) == 10 and len(set(retvals)) == 1

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Execute test "
            "`tests/qa/utilities_lambdify_generated_function_output_determinism_test.py::"
            "TestUtilitiesLambdifyGeneratedFunctionOutputDeterminismQA::"
            "test_utilities_lambdify_generated_function_output_determinism_case` "
            "exactly 10 independent times with identical inputs. In each execution, "
            "`sympy.utilities.lambdify.lambdify` in `sympy/utilities/lambdify.py` "
            "is called once with (`x`, `sin(x) + x**2`, module=`\"math\"`). "
            "Is the returned value identical across all 10 executions? "
            "Return JSON with exactly one key: `{\"invariant_exists\": <bool>}`."
        ),
        "template_answer": {
            "invariant_exists": "bool",
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
