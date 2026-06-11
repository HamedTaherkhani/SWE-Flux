#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


TARGET_FUNC = "control.margins._poly_z_wstab"
TARGET_FILE = "/testbed/control/margins.py"
TARGET_VARIABLE = "wdt0"

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
    active = False
    current_value: float | None = None

    for raw_line in trace_text.splitlines():
        match = TRACE_RE.match(raw_line)
        if not match:
            continue

        if match.group("path") != TARGET_FILE or match.group("func") != TARGET_FUNC:
            continue

        event = match.group("event")
        locals_dict = ast.literal_eval(match.group("locals"))
        if event == "call":
            active = True
            current_value = None
            continue

        if active and TARGET_VARIABLE in locals_dict:
            current_value = _parse_number(locals_dict[TARGET_VARIABLE])

        if active and event in {"return", "exception"}:
            if current_value is None:
                raise ValueError(f"Missing {TARGET_VARIABLE!r} for invocation.")
            values.append(current_value)
            active = False

    if len(values) != 10:
        raise ValueError(
            f"Expected 10 observed {TARGET_VARIABLE!r} values, "
            f"observed {len(values)}: {values!r}."
        )

    return {
        "min_value": round(min(values), 6),
        "max_value": round(max(values), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default="/testbed/logs/qa_instances/margins_poly_z_wstab_wdt0_value_range_suite/trace.log")
    parser.add_argument("--out", default="/testbed/logs/qa_instances/margins_poly_z_wstab_wdt0_value_range_suite/oracle.json")
    args = parser.parse_args()

    answer = extract_value_range(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "M3_ProgramState",
        "question": (
            "Run the full test suite in "
            "`tests/qa/margins_poly_z_wstab_wdt0_value_range_suite_test.py` "
            "(all 10 test methods in `TestDiscreteStabilityGuessRangeQA`, in "
            "file order: `test_case_01`, `test_case_02`, `test_case_03`, "
            "`test_case_04`, `test_case_05`, `test_case_06`, `test_case_07`, "
            "`test_case_08`, `test_case_09`, and `test_case_10`). The tests "
            "import the target helper directly with `from control.margins "
            "import _poly_z_invz, _poly_z_wstab` and construct discrete "
            "transfer functions with `from control.xferfcn import tf`. Focus "
            "on the local variable `wdt0` inside `control.margins._poly_z_wstab`. "
            "It is computed from a geometric frequency grid and used as the "
            "initial optimizer value at line 159, `x0=[wdt0]`. Across the 10 "
            "invocations of `_poly_z_wstab`, what are the minimum and maximum "
            "values of `wdt0`? Return only `min_value` and `max_value` as "
            "numbers rounded to 6 digits after the decimal point."
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
