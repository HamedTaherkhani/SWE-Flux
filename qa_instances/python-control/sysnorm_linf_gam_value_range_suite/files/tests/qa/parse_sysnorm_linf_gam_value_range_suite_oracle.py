#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


TARGET_FUNC = "control.sysnorm.system_norm"
TARGET_FILE = "/testbed/control/sysnorm.py"
TARGET_LINE = 315
TARGET_VARIABLE = "gam"

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/control/(?!tests/)[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
    r".*? locals=(?P<locals>\{.*\})$"
)


def _parse_number(value_repr: str) -> float:
    if value_repr.startswith("np."):
        match = re.match(r"np\.[A-Za-z0-9_]+\((?P<value>[-+0-9.eE]+)\)", value_repr)
        if not match:
            raise ValueError(f"Cannot parse NumPy scalar repr: {value_repr!r}")
        return float(match.group("value"))
    return float(value_repr)


def extract_value_range(trace_text: str) -> dict:
    values: list[float] = []

    for raw_line in trace_text.splitlines():
        match = TRACE_RE.match(raw_line)
        if not match:
            continue
        if (
            match.group("path") != TARGET_FILE
            or int(match.group("lineno")) != TARGET_LINE
            or match.group("func") != TARGET_FUNC
            or match.group("event") != "line"
        ):
            continue
        locals_dict = ast.literal_eval(match.group("locals"))
        if TARGET_VARIABLE in locals_dict:
            values.append(_parse_number(locals_dict[TARGET_VARIABLE]))

    if not values:
        raise ValueError(f"No observed {TARGET_VARIABLE!r} values at line {TARGET_LINE}.")

    return {
        "min_value": round(min(values), 6),
        "max_value": round(max(values), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default="/testbed/logs/qa_instances/sysnorm_linf_gam_value_range_suite/trace.log")
    parser.add_argument("--out", default="/testbed/logs/qa_instances/sysnorm_linf_gam_value_range_suite/oracle.json")
    args = parser.parse_args()

    answer = extract_value_range(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "M4_ProgramState",
        "question": (
            "Run the full test suite in "
            "`tests/qa/sysnorm_linf_gam_value_range_suite_test.py` (all 10 "
            "test methods in `TestLinfBisectionStateRangeQA`, in file order: "
            "`test_case_01`, `test_case_02`, `test_case_03`, `test_case_04`, "
            "`test_case_05`, `test_case_06`, `test_case_07`, `test_case_08`, "
            "`test_case_09`, and `test_case_10`). The tests import the target "
            "directly with `from control.sysnorm import system_norm` and build "
            "state-space systems with `from control.statesp import ss`. Focus "
            "on the local variable `gam` inside `control.sysnorm.system_norm` "
            "on the SciPy L-infinity norm path. It is assigned as the current "
            "bisection midpoint at line 314 and used in the Hamiltonian test at "
            "line 315, `if any(np.isclose(la.eigvals(_Hamilton_matrix(gam)).real, "
            "0.0)):`. Across all executions of line 315 caused by this suite, "
            "what are the minimum and maximum values reached by `gam`? Return "
            "only `min_value` and `max_value` as numbers rounded to 6 digits "
            "after the decimal point."
        ),
        "template_answer": {
            "min_value": "float",
            "max_value": "float",
        },
        "oracle_answer": answer,
    }
    Path(args.out).write_text(
        json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
