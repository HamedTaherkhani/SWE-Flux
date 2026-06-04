#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

TARGET = "pybamm.expression_tree.operations.serialise.Serialise.load_model"
PREFIX = "pybamm.expression_tree.operations.serialise."
RE = re.compile(r"^.*? (?P<func>\S+) event=(?P<event>call|return|exception)\b(?: exc=(?P<kind>[A-Za-z_]\w*):)?")


def extract(lines):
    depth, calls, kinds = 0, 0, set()
    for line in lines:
        match = RE.match(line)
        if not match:
            continue
        func, event, kind = match.group("func", "event", "kind")
        if event == "call" and func == TARGET:
            calls += 1
            depth += 1
            continue
        if depth and event == "exception" and func.startswith(PREFIX) and kind:
            kinds.add(kind)
        if depth and event == "return" and func == TARGET:
            depth -= 1
    if calls != 10 or depth != 0:
        raise ValueError(f"Expected 10 complete target calls, found calls={calls}, depth={depth}")
    return {"exception_types": sorted(kinds)}


def main():
    p = argparse.ArgumentParser(); p.add_argument("--trace-log", required=True); p.add_argument("--out", required=True); a = p.parse_args()
    qa = {
        "question_kind": "M6_ExceptionalBehavior",
        "question": (
            "Run `tests/qa/serialise_load_model_exception_diversity_suite_test.py` methods "
            "`test_case_01` through `test_case_10` in `TestSerialiseLoadModelExceptionDiversityQA`, "
            "executed sequentially in file order. Each test calls `_load` once, which calls "
            "`pybamm.expression_tree.operations.serialise.Serialise.load_model` exactly once and "
            "generically catches any exception that escapes it, so all tests pass. JSON/model "
            "preparation before `_load` is outside the target dynamic extent. Across the dynamic "
            "extent from each `Serialise.load_model` call until its matching return, including nested "
            "calls, identify every concrete exception class for which a Python `exception` trace event "
            "occurs. Include both exceptions caught internally by PyBaMM and exceptions that escape the "
            "target and are caught by `_load`. Consider only frames whose source file is under "
            "`src/pybamm` and whose trace name starts with "
            "`pybamm.expression_tree.operations.serialise.`. Ignore pytest and test-helper frames. "
            "Which exception kinds are encountered? Return `exception_types` as unique class names "
            "sorted lexicographically."
        ),
        "template_answer": {"exception_types": ["str"]},
        "oracle_answer": extract(Path(a.trace_log).open()),
    }
    Path(a.out).write_text(json.dumps(qa, indent=2) + "\n"); print(json.dumps(qa, indent=2))


if __name__ == "__main__": main()
