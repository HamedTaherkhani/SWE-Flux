#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "discretisation_process_model_call_coverage_suite"
TARGET_FUNC = "pybamm.discretisations.discretisation.Discretisation.process_model"
EXPECTED_TARGET_CALLS = 10
PREFIXES = (
    "pybamm.discretisations.discretisation.",
    "pybamm.spatial_methods.",
    "pybamm.models.base_model.",
    "pybamm.models.event.",
    "pybamm.expression_tree.",
)
CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/src/pybamm/(?!tests/)[^:]+):\d+ "
    r"(?P<func>\S+) event=(?P<event>call|return|exception)\b"
)


def extract(trace_text):
    depth = 0
    target_calls = 0
    covered = set()
    for line in trace_text.splitlines():
        match = CALL_RE.match(line)
        if not match:
            continue
        func, event, path = match.group("func", "event", "path")
        if event == "call" and func == TARGET_FUNC:
            target_calls += 1
            depth += 1
            covered.add((path.replace("/testbed/", ""), func))
            continue
        if depth and event == "call" and func.startswith(PREFIXES) and "<" not in func:
            covered.add((path.replace("/testbed/", ""), func))
        if depth and func == TARGET_FUNC and event in {"return", "exception"}:
            depth = max(0, depth - 1)
    if not covered:
        raise ValueError("No calls collected while Discretisation.process_model was active")
    if target_calls != EXPECTED_TARGET_CALLS:
        raise ValueError(f"Expected {EXPECTED_TARGET_CALLS} target calls, found {target_calls}")
    return {"covered_functions": [{"file": f, "func": n} for f, n in sorted(covered)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log")
    parser.add_argument("--out", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json")
    args = parser.parse_args()
    answer = extract(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "M6_InterProceduralCFG",
        "question": (
            "Run the full test suite in "
            "`tests/qa/discretisation_process_model_call_coverage_suite_test.py` "
            "(methods `test_case_01` through `test_case_10` in "
            "`TestDiscretisationProcessModelCallCoverageQA`, executed sequentially in "
            "file order). The tests construct zero-dimensional ODE and DAE models "
            "and finite-volume spatial diffusion models, then call "
            "`Discretisation.process_model(...)` exactly once per test. Focus on calls "
            "made while "
            "`pybamm.discretisations.discretisation.Discretisation.process_model` is "
            "active: from each target call until its matching return or exception, "
            "including nested calls and taking the union over all tests. Include the "
            "target itself. Count a function only when its Python frame produces a "
            "`call` trace event within that dynamic extent. Consider only frames whose "
            "source file is under `src/pybamm` and whose trace name starts "
            "with `pybamm.discretisations.discretisation.`, "
            "`pybamm.spatial_methods.`, `pybamm.models.base_model.`, "
            "`pybamm.models.event.`, or `pybamm.expression_tree.`. Ignore calls from "
            "`src/pybamm/tests` and exclude generated code-object names containing "
            "angle brackets. Use `file` as the forward-slash path relative to the "
            "repository root. Use `func` as the frame module name followed by `.` and "
            "the code object's `co_qualname`. "
            "Which unique functions are covered at least once? Return "
            "`covered_functions` as objects with keys `file` and `func`, sorted by "
            "`file` and then `func`."
        ),
        "template_answer": {"covered_functions": [{"file": "str", "func": "str"}]},
        "oracle_answer": answer,
    }
    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
