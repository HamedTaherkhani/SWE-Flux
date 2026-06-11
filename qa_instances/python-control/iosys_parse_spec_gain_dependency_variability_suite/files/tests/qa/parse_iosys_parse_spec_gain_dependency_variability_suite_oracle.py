#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

INSTANCE_ID = "iosys_parse_spec_gain_dependency_variability_suite"
TARGET_FILE = "/testbed/control/iosys.py"
TARGET_FUNC = "control.iosys._parse_spec"
TEST_NAMES = [f"test_case_{i:02d}" for i in range(1, 11)]

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/control/iosys.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) (?P<rest>.*)$",
    re.MULTILINE,
)


def call_spec(rest: str):
    match = re.search(r"locals=(\{.*\})$", rest)
    locals_dict = ast.literal_eval(match.group(1))
    return ast.literal_eval(locals_dict["spec"])


def source_for_spec(spec) -> list[dict[str, int | str]]:
    if isinstance(spec, str):
        system_spec, signal_spec = (spec.split(".", 1) + [None])[:2]
        if system_spec.startswith("-"):
            return [{"variable": "system_spec", "line": 1263}]
        if isinstance(signal_spec, str) and signal_spec.startswith("-"):
            return [{"variable": "signal_spec", "line": 1266}]
        return [{"variable": "gain", "line": 1269}]
    if isinstance(spec, tuple):
        system_spec = spec[0]
        signal_spec = spec[1] if len(spec) >= 2 else None
        if len(spec) >= 3:
            return [{"variable": "spec", "line": 1252}]
        if isinstance(system_spec, str) and system_spec.startswith("-"):
            return [{"variable": "system_spec", "line": 1263}]
        if isinstance(signal_spec, str) and signal_spec.startswith("-"):
            return [{"variable": "signal_spec", "line": 1266}]
        return [{"variable": "gain", "line": 1269}]
    return [{"variable": "gain", "line": 1269}]


def extract(trace_text: str):
    out = []
    current = None
    for match in TRACE_RE.finditer(trace_text):
        if match.group("path") != TARGET_FILE or match.group("func") != TARGET_FUNC:
            continue
        if match.group("event") == "call":
            current = source_for_spec(call_spec(match.group("rest")))
        elif match.group("event") == "return":
            out.append(current)
            current = None
    if len(out) != 10:
        raise RuntimeError(f"expected 10 calls, found {len(out)}")
    return [
        {
            "test": test,
            "dependencies": sorted(deps, key=lambda item: (item["variable"], item["line"])),
        }
        for test, deps in zip(TEST_NAMES, out)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log")
    parser.add_argument("--out", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json")
    args = parser.parse_args()
    dependencies_by_test = extract(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "M4_DataFlow",
        "question": (
            "Run the full test suite in `tests/qa/iosys_parse_spec_gain_dependency_variability_suite_test.py` "
            "(all 10 test methods in `TestParseSpecGainDependencyVariabilityQA`, in file order: "
            "`test_case_01`, `test_case_02`, `test_case_03`, `test_case_04`, `test_case_05`, "
            "`test_case_06`, `test_case_07`, `test_case_08`, `test_case_09`, and `test_case_10`). "
            "The tests import the target directly with `from control.iosys import _parse_spec`. "
            "Focus only on local variable `gain` in `control.iosys._parse_spec` in file `control/iosys.py`, "
            "at the function return. For each test method, identify which variable read, and at which line, "
            "the returned `gain` dynamically depends on. Include branch-condition variables when `gain` is "
            "assigned a literal selected by that branch. "
            "Return `dependencies_by_test` as a list of objects with exactly these keys: `test`, "
            "`dependencies`. Each `dependencies` value must be a list of objects with exactly these keys: "
            "`variable`, `line`. Sort tests in file order, and sort each `dependencies` list by `variable` "
            "using Python's default case-sensitive string ordering, then by `line` ascending."
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
