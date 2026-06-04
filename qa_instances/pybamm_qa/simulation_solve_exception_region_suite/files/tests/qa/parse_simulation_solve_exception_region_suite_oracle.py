#!/usr/bin/env python3
import argparse, json, re, xml.etree.ElementTree as ET
from pathlib import Path

CLASS = "TestSimulationSolveExceptionRegionQA"
CASE_RE = re.compile(r"test_case_(\d{2})$")
EXCEPTION_RE = re.compile(r"(?:^|[.\s])(?P<kind>SolverError|ValueError)(?=:)")


def extract(report):
    outcomes = {}
    for case in ET.parse(report).iter("testcase"):
        name = case.attrib.get("name", "")
        if not CASE_RE.fullmatch(name) or case.attrib.get("classname", "").split(".")[-1] != CLASS:
            continue
        failures = list(case.findall("failure")) + list(case.findall("error"))
        if not failures:
            outcomes[name] = None
        else:
            details = f"{failures[0].attrib.get('message', '')}\n{failures[0].text or ''}"
            kinds = EXCEPTION_RE.findall(details)
            if len(failures) != 1 or not kinds:
                raise ValueError(f"Could not identify one escaping exception for {name}")
            outcomes[name] = kinds[-1]
    expected = [f"test_case_{i:02d}" for i in range(1, 11)]
    if sorted(outcomes) != expected:
        raise ValueError(f"Expected {expected}, found {sorted(outcomes)}")
    return {
        "safe_tests": [t for t in expected if outcomes[t] is None],
        "crashing_tests": [{"test": t, "exception_type": outcomes[t]} for t in expected if outcomes[t] is not None],
    }


def main():
    p = argparse.ArgumentParser(); p.add_argument("--report", required=True); p.add_argument("--out", required=True); a = p.parse_args()
    qa = {
        "question_kind": "M6_ExceptionalBehavior",
        "question": (
            "Run `tests/qa/simulation_solve_exception_region_suite_test.py` methods "
            "`test_case_01` through `test_case_10` in `TestSimulationSolveExceptionRegionQA`, "
            "executed sequentially in file order. Each test calls `_solve` once, which calls "
            "`pybamm.simulation.Simulation.solve` exactly once. Simulation, model, and solver "
            "construction before that call is outside the target dynamic extent. Classify a "
            "test as crashing only when an exception escapes the `Simulation.solve(...)` call; "
            "classify it as safe when that call returns normally. For each crashing test, report "
            "the concrete escaping exception class name. Ignore pytest framework activity and "
            "the assertion after a successful call. In both answer fields, identify tests only by their exact bare method names, for example `test_case_01`; do not use ordinal labels, class-qualified names, file paths, or pytest node IDs. Which tests are safe and which crash? Return "
            "`safe_tests` in file order and `crashing_tests` in file order, with each crashing "
            "entry containing `test` and `exception_type`."
        ),
        "template_answer": {"safe_tests": ["str"], "crashing_tests": [{"test": "str", "exception_type": "str"}]},
        "oracle_answer": extract(a.report),
    }
    Path(a.out).write_text(json.dumps(qa, indent=2) + "\n"); print(json.dumps(qa, indent=2))


if __name__ == "__main__": main()
