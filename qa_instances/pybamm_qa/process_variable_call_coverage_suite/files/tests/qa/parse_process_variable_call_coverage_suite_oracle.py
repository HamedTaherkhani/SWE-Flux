#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

ID = "process_variable_call_coverage_suite"
TARGET = "pybamm.solvers.processed_variable.process_variable"
PREFIXES = ("pybamm.solvers.processed_variable.", "pybamm.solvers.base_processed_variable.", "pybamm.solvers.solution.", "pybamm.expression_tree.")
RE = re.compile(r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/src/pybamm/(?!tests/)[^:]+):\d+ (?P<func>\S+) event=(?P<event>call|return|exception)\b")


def extract(text):
    depth, calls, covered = 0, 0, set()
    for line in text.splitlines():
        m = RE.match(line)
        if not m:
            continue
        func, event, path = m.group("func", "event", "path")
        if event == "call" and func == TARGET:
            calls += 1; depth += 1; covered.add((path.replace("/testbed/", ""), func)); continue
        if depth and event == "call" and func.startswith(PREFIXES) and "<" not in func:
            covered.add((path.replace("/testbed/", ""), func))
        if depth and func == TARGET and event in {"return", "exception"}:
            depth = max(0, depth - 1)
    if calls != 10:
        raise ValueError(f"Expected 10 target calls, found {calls}")
    return {"covered_functions": [{"file": f, "func": n} for f, n in sorted(covered)]}


def main():
    p=argparse.ArgumentParser(); p.add_argument("--trace-log"); p.add_argument("--out"); a=p.parse_args()
    qa={"question_kind":"M2_InterProceduralCFG","question":(
        "Run `tests/qa/process_variable_call_coverage_suite_test.py` methods "
        "`test_case_01` through `test_case_10` in `TestProcessVariableCallCoverageQA`, "
        "executed sequentially in file order. Each test obtains one processed output "
        "through `Solution.__getitem__`, which calls "
        "`pybamm.solvers.processed_variable.process_variable` exactly once. Focus on "
        "Python `call` trace events occurring from each target call until its matching "
        "return or exception, including nested calls, and take the union over all tests. "
        "Include the target itself. Consider only frames whose source file is under "
        "`src/pybamm` and whose trace name starts with "
        "`pybamm.solvers.processed_variable.`, `pybamm.solvers.base_processed_variable.`, "
        "`pybamm.solvers.solution.`, or `pybamm.expression_tree.`. Ignore calls from "
        "`src/pybamm/tests` and exclude code-object names containing angle brackets. "
        "Use repository-relative forward-slash paths for `file`. Use `func` as the frame "
        "module name followed by `.` and the code object's `co_qualname`. Which unique "
        "functions are covered? Return `covered_functions` with keys `file` and `func`, "
        "sorted by `file` and then `func`."
    ),"template_answer":{"covered_functions":[{"file":"str","func":"str"}]},"oracle_answer":extract(Path(a.trace_log).read_text())}
    Path(a.out).write_text(json.dumps(qa,indent=2)+"\n"); print(json.dumps(qa,indent=2))
if __name__=="__main__": main()
