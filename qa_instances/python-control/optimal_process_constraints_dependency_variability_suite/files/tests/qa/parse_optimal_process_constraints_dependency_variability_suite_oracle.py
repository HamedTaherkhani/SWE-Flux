#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "optimal_process_constraints_dependency_variability_suite"
TARGET_FILE = "/testbed/control/optimal.py"
TARGET_FUNC = "control.optimal._process_constraints"
TEST_NAMES = [f"test_case_{i:02d}" for i in range(1, 11)]

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/control/optimal.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) ",
    re.MULTILINE,
)


def extract(trace_text: str):
    out = []
    current: list[dict[str, int | str]] | None = None
    for match in TRACE_RE.finditer(trace_text):
        if match.group("path") != TARGET_FILE or match.group("func") != TARGET_FUNC:
            continue
        event = match.group("event")
        lineno = int(match.group("lineno"))
        if event == "call":
            current = []
        elif event == "line" and current is not None:
            if lineno == 2554:
                current.append({"variable": "clist", "line": 2553})
            elif lineno == 2557:
                current.append({"variable": "clist", "line": 2557})
            elif lineno == 2569:
                current.append({"variable": "constraint", "line": 2569})
            elif lineno in {2571, 2572, 2573}:
                if lineno == 2572:
                    current.append({"variable": "constraint.A", "line": 2572})
                elif lineno == 2573:
                    current.extend([
                        {"variable": "constraint.lb", "line": 2573},
                        {"variable": "constraint.ub", "line": 2573},
                    ])
            elif lineno in {2575, 2576, 2577}:
                if lineno == 2576:
                    current.append({"variable": "constraint.fun", "line": 2576})
                elif lineno == 2577:
                    current.extend([
                        {"variable": "constraint.lb", "line": 2577},
                        {"variable": "constraint.ub", "line": 2577},
                    ])
        elif event == "return" and current is not None:
            out.append(current)
            current = None
    if len(out) != 10:
        raise RuntimeError(f"expected 10 calls, found {len(out)}")
    normalized = []
    for test, deps in zip(TEST_NAMES, out):
        unique = {
            (dep["variable"], dep["line"]): dep
            for dep in deps
        }
        normalized.append({
            "test": test,
            "dependencies": sorted(
                unique.values(), key=lambda item: (item["variable"], item["line"])),
        })
    return normalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log")
    parser.add_argument("--out", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json")
    args = parser.parse_args()
    dependencies_by_test = extract(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "M4_DataFlow",
        "question": (
            "Run the full test suite in `tests/qa/optimal_process_constraints_dependency_variability_suite_test.py` "
            "(all 10 test methods in `TestProcessConstraintsDependencyVariabilityQA`, in file order: "
            "`test_case_01`, `test_case_02`, `test_case_03`, `test_case_04`, `test_case_05`, "
            "`test_case_06`, `test_case_07`, `test_case_08`, `test_case_09`, and `test_case_10`). "
            "The tests import the target directly with `from control.optimal import _process_constraints`. "
            "Focus only on local variable `constraint_list` in `control.optimal._process_constraints` in file "
            "`control/optimal.py`, at the function return. For each test method, identify which variable or "
            "attribute read, and at which line, the returned `constraint_list` dynamically depends on. Include "
            "branch-condition variables when `constraint_list` receives a literal selected by that branch. "
            "Return `dependencies_by_test` as a list of objects with exactly these keys: `test`, `dependencies`. "
            "Each `dependencies` value must be a list of objects with exactly these keys: `variable`, `line`. "
            "Sort tests in file order, and sort each `dependencies` list by `variable` using Python's default "
            "case-sensitive string ordering, then by `line` ascending."
        ),
        "template_answer": {
            "dependencies_by_test": [
                {"test": "str", "dependencies": [{"variable": "str", "line": "int"}]}
            ]
        },
        "oracle_answer": {"dependencies_by_test": dependencies_by_test},
    }
    Path(args.out).write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
