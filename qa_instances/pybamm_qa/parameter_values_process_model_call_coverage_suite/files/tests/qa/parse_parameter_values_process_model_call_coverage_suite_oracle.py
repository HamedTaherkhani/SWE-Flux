#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


INSTANCE_ID = "parameter_values_process_model_call_coverage_suite"
TARGET_FUNC = "pybamm.parameters.parameter_values.ParameterValues.process_model"
EXPECTED_TARGET_CALLS = 10
INCLUDED_PREFIXES = (
    "pybamm.parameters.parameter_values.",
    "pybamm.models.base_model.",
    "pybamm.expression_tree.",
)

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/src/pybamm/(?!tests/)[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|return|exception)\b"
)


def _relative_file(path: str) -> str:
    return path.replace("/testbed/", "")


def extract_call_coverage(trace_text: str) -> dict:
    active_depth = 0
    target_calls = 0
    covered: set[tuple[str, str]] = set()

    for raw_line in trace_text.splitlines():
        match = CALL_RE.match(raw_line)
        if not match:
            continue

        func = match.group("func")
        event = match.group("event")
        path = match.group("path")

        if event == "call" and func == TARGET_FUNC:
            target_calls += 1
            active_depth += 1
            covered.add((_relative_file(path), func))
            continue

        if active_depth > 0 and event == "call":
            if func.startswith(INCLUDED_PREFIXES) and "<" not in func:
                covered.add((_relative_file(path), func))

        if active_depth > 0 and func == TARGET_FUNC and event in {"return", "exception"}:
            active_depth = max(0, active_depth - 1)

    if not covered:
        raise ValueError("No call events were collected while process_model was active.")
    if target_calls != EXPECTED_TARGET_CALLS:
        raise ValueError(
            f"Expected {EXPECTED_TARGET_CALLS} target calls, found {target_calls}."
        )

    return {
        "covered_functions": [
            {"file": file, "func": func}
            for file, func in sorted(covered, key=lambda item: (item[0], item[1]))
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log",
    )
    parser.add_argument(
        "--out",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_call_coverage(trace_text)

    qa = {
        "question_kind": "M6_InterProceduralCFG",
        "question": (
            "Run the full test suite in "
            "`tests/qa/parameter_values_process_model_call_coverage_suite_test.py` "
            "(all 10 test methods in "
            "`TestParameterValuesProcessModelCallCoverageQA`, executed sequentially "
            "in file order: "
            "`test_case_01`, `test_case_02`, `test_case_03`, `test_case_04`, "
            "`test_case_05`, `test_case_06`, `test_case_07`, `test_case_08`, "
            "`test_case_09`, `test_case_10`). The tests construct "
            "`pybamm.ParameterValues` and `pybamm.BaseModel` objects containing "
            "parameterized rhs equations, optional algebraic equations, optional "
            "boundary conditions, variables, events, function parameters, and "
            "non-extrapolating interpolants; each test calls "
            "`ParameterValues.process_model(...)` exactly once. Focus on calls made "
            "while "
            "`pybamm.parameters.parameter_values.ParameterValues.process_model` is "
            "active; this means the dynamic extent from each call to `process_model` "
            "until its matching return or exception, including nested calls made by "
            "`process_model`, and taking the union over all tests. Include "
            "`pybamm.parameters.parameter_values.ParameterValues.process_model` "
            "itself. Within that dynamic extent, consider only functions whose trace "
            "names start with one of `pybamm.parameters.parameter_values.`, "
            "`pybamm.models.base_model.`, or `pybamm.expression_tree.`, and ignore "
            "calls from `src/pybamm/tests`. Count a function only when its Python frame "
            "produces a `call` trace event within that dynamic extent, and consider "
            "only frames whose source file is under `src/pybamm`. Exclude generated "
            "code-object names "
            "containing angle brackets, such as `<listcomp>`, `<genexpr>`, and "
            "`<lambda>`. For each covered function, use `file` as the forward-slash "
            "path relative to the repository root, such as "
            "`src/pybamm/parameters/parameter_values.py`. Use `func` as "
            "`<module>.<code object qualified name>`, where `<module>` is the "
            "function frame's module name and `<code object qualified name>` is the "
            "Python code object's `co_qualname`, so class methods include their "
            "class name, for example "
            "`pybamm.parameters.parameter_values.ParameterValues.process_model`. "
            "Which unique functions are covered at least once by this suite? Return "
            "`covered_functions` as a list of objects with keys `file` and `func`, "
            "sorted by `file` and then `func`."
        ),
        "template_answer": {
            "covered_functions": [
                {
                    "file": "str",
                    "func": "str",
                }
            ]
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(
        json.dumps(qa, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
