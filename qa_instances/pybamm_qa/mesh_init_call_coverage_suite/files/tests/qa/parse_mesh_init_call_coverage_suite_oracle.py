#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

ID = "mesh_init_call_coverage_suite"
TARGET = "pybamm.meshes.meshes.Mesh.__init__"
EXPECTED_TARGET_CALLS = 10
PREFIXES = ("pybamm.meshes.", "pybamm.expression_tree.")
RE = re.compile(r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/src/pybamm/(?!tests/)[^:]+):\d+ (?P<func>\S+) event=(?P<event>call|return|exception)\b")


def extract(text):
    depth, target_calls, covered = 0, 0, set()
    for line in text.splitlines():
        m = RE.match(line)
        if not m:
            continue
        func, event, path = m.group("func", "event", "path")
        if event == "call" and func == TARGET:
            target_calls += 1
            depth += 1
            covered.add((path.replace("/testbed/", ""), func))
            continue
        if depth and event == "call" and func.startswith(PREFIXES) and "<" not in func:
            covered.add((path.replace("/testbed/", ""), func))
        if depth and func == TARGET and event in {"return", "exception"}:
            depth = max(0, depth - 1)
    if not covered:
        raise ValueError("No calls collected while Mesh.__init__ was active")
    if target_calls != EXPECTED_TARGET_CALLS:
        raise ValueError(f"Expected {EXPECTED_TARGET_CALLS} target calls, found {target_calls}")
    return {"covered_functions": [{"file": f, "func": n} for f, n in sorted(covered)]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{ID}/trace.log")
    p.add_argument("--out", default=f"/testbed/logs/qa_instances/{ID}/oracle.json")
    a = p.parse_args()
    qa = {
        "question_kind": "M2_InterProceduralCFG",
        "question": (
            "Run the full test suite in `tests/qa/mesh_init_call_coverage_suite_test.py` "
            "(methods `test_case_01` through `test_case_10` in "
            "`TestMeshInitCallCoverageQA`, executed sequentially in file order). "
            "The tests construct meshes using uniform, Chebyshev, exponential, symbolic "
            "uniform, spherical-polar, multi-domain, and zero-dimensional configurations; "
            "each test calls `pybamm.Mesh(...)` exactly once. Focus on calls made while "
            "`pybamm.meshes.meshes.Mesh.__init__` is active, from each target call until "
            "its matching return or exception, including nested calls and taking the union "
            "over all tests. Include the target itself. Consider only trace names starting "
            "with `pybamm.meshes.` or `pybamm.expression_tree.`. Count a function only "
            "when its Python frame produces a `call` trace event within that dynamic "
            "extent, and consider only frames whose source file is under `src/pybamm`. "
            "Ignore calls from "
            "`src/pybamm/tests` and exclude generated code-object names containing angle "
            "brackets. Use repository-relative forward-slash paths for `file`. Use "
            "`func` as the frame module name followed by `.` and the code object's "
            "`co_qualname`. Which unique functions "
            "are covered? Return `covered_functions` sorted by `file` and then `func`."
        ),
        "template_answer": {"covered_functions": [{"file": "str", "func": "str"}]},
        "oracle_answer": extract(Path(a.trace_log).read_text()),
    }
    Path(a.out).write_text(json.dumps(qa, indent=2) + "\n")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
