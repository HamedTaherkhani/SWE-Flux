#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

TARGET = "pybamm.models.full_battery_models.lithium_ion.spm.SPM.__init__"
PREFIXES = (
    "pybamm.models.full_battery_models.",
    "pybamm.models.base_model.",
    "pybamm.models.submodels.particle.",
    "pybamm.models.submodels.interface.",
    "pybamm.models.submodels.thermal.",
    "pybamm.citations.",
)
RE = re.compile(r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/src/pybamm/(?!tests/)[^:]+):\d+ (?P<func>\S+) event=(?P<event>call|return|exception)\b")


def extract(lines):
    depth, calls, covered = 0, 0, set()
    for line in lines:
        match = RE.match(line)
        if not match:
            continue
        func, event, path = match.group("func", "event", "path")
        if event == "call" and func == TARGET:
            calls += 1
            depth += 1
            covered.add((path.replace("/testbed/", ""), func))
            continue
        if depth and event == "call" and func.startswith(PREFIXES) and "<" not in func:
            covered.add((path.replace("/testbed/", ""), func))
        if depth and func == TARGET and event in {"return", "exception"}:
            depth = max(0, depth - 1)
    if calls != 10:
        raise ValueError(f"Expected 10 target calls, found {calls}")
    return {"covered_functions": [{"file": file, "func": func} for file, func in sorted(covered)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log")
    parser.add_argument("--out")
    args = parser.parse_args()
    qa = {
        "question_kind": "M6_InterProceduralCFG",
        "question": (
            "Run `tests/qa/lithium_ion_spm_init_call_coverage_suite_test.py` methods "
            "`test_case_01` through `test_case_10` in `TestLithiumIonSPMInitCallCoverageQA`, "
            "executed sequentially in file order. Each test calls "
            "`pybamm.models.full_battery_models.lithium_ion.spm.SPM.__init__` exactly once "
            "through `pybamm.lithium_ion.SPM(...)`. Focus on Python `call` trace events "
            "occurring from each target call until its matching return or exception, "
            "including nested calls, and take the union over all tests. Include the target "
            "itself. Consider only frames whose source file is under `src/pybamm` and whose "
            "trace name starts with `pybamm.models.full_battery_models.`, "
            "`pybamm.models.base_model.`, `pybamm.models.submodels.particle.`, "
            "`pybamm.models.submodels.interface.`, `pybamm.models.submodels.thermal.`, "
            "or `pybamm.citations.`. Ignore calls from "
            "`src/pybamm/tests` and exclude code-object names containing angle brackets. "
            "Use repository-relative forward-slash paths for `file`. Use `func` as the frame "
            "module name followed by `.` and the code object's `co_qualname`. Which unique "
            "functions are covered? Return `covered_functions` with keys `file` and `func`, "
            "sorted by `file` and then `func`."
        ),
        "template_answer": {"covered_functions": [{"file": "str", "func": "str"}]},
        "oracle_answer": extract(Path(args.trace_log).open()),
    }
    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
