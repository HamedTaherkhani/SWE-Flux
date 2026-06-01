#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

INSTANCE_ID = "config_process_param_dependency_variability_suite"
TARGET_FILE = "/testbed/control/config.py"
TARGET_FUNC = "control.config._process_param"

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/control/config.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
    r"(?P<rest>.*)$",
    re.MULTILINE,
)

TEST_NAMES = [f"test_case_{i:02d}" for i in range(1, 11)]
LEGACY_KEYS = ("time_points", "tout")
ALIAS_KEYS = ("T", "time")


def extract_str(rest: str, name: str) -> str | None:
    match = re.search(rf"\b{name}=('(?:[^'\\]|\\.)*')", rest)
    if not match:
        return None
    return json.loads(match.group(1).replace("\\'", "'").replace('"', '\\"').replace("'", '"'))


def extract_kwargs_keys(rest: str) -> set[str]:
    match = re.search(r"locals=(\{.*\})$", rest)
    if not match:
        return set()
    locals_dict = ast.literal_eval(match.group(1))
    kwargs_repr = locals_dict.get("kwargs", "{}")
    kwargs_dict = ast.literal_eval(kwargs_repr)
    return set(kwargs_dict)


def extract_dependencies(trace_text: str) -> list[dict[str, object]]:
    per_call: list[set[str]] = []
    current_source: str | None = None

    for match in TRACE_RE.finditer(trace_text):
        if match.group("path") != TARGET_FILE or match.group("func") != TARGET_FUNC:
            continue

        event = match.group("event")
        rest = match.group("rest")

        if event == "call":
            current_kwargs = extract_kwargs_keys(rest)
            current_source = "kwargs['timepts']" if "timepts" in current_kwargs else "defval"
            for key in LEGACY_KEYS:
                if key in current_kwargs:
                    current_source = f"kwargs['{key}']"
            for key in ALIAS_KEYS:
                if key in current_kwargs:
                    current_source = f"kwargs['{key}']"
            continue

        if event == "return":
            if current_source is None:
                raise RuntimeError("return event encountered before call event")
            per_call.append({current_source})
            current_source = None

    if len(per_call) != len(TEST_NAMES):
        raise RuntimeError(f"expected {len(TEST_NAMES)} traced calls, found {len(per_call)}")

    return [
        {"test": test_name, "dependencies": sorted(deps)}
        for test_name, deps in zip(TEST_NAMES, per_call)
    ]


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
    dependencies_by_test = extract_dependencies(trace_text)

    qa = {
        "question_kind": "M5_DataFlow",
        "question": (
            "Run the full test suite in "
            "`tests/qa/config_process_param_dependency_variability_suite_test.py` "
            "(all 10 test methods in `TestProcessParamDependencyVariabilityQA`, "
            "in file order: `test_case_01`, `test_case_02`, `test_case_03`, "
            "`test_case_04`, `test_case_05`, `test_case_06`, `test_case_07`, "
            "`test_case_08`, `test_case_09`, and `test_case_10`). The tests import "
            "the target directly with `from control.config import _process_param`. "
            "Focus only on local variable `newval` in "
            "`control.config._process_param` in file `control/config.py`, at the "
            "function return. For each test method, identify which input source "
            "the returned value of `newval` dynamically depends on. Use only these "
            "source labels when applicable: `defval`, `kwargs['timepts']`, "
            "`kwargs['T']`, `kwargs['time']`, `kwargs['time_points']`, and "
            "`kwargs['tout']`. If multiple aliases are present with the same value, "
            "report the source whose assignment to `newval` occurs last on the "
            "executed path. Return `dependencies_by_test` as a list of objects with "
            "exactly these keys: `test`, `dependencies`. Sort tests in file order, "
            "and sort each `dependencies` list lexicographically using Python's "
            "default case-sensitive string ordering."
        ),
        "template_answer": {
            "dependencies_by_test": [
                {
                    "test": "str",
                    "dependencies": ["str"],
                }
            ]
        },
        "oracle_answer": {
            "dependencies_by_test": dependencies_by_test,
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
