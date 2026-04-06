#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/faker/utils/distribution.py"
TARGET_FUNC = "faker.utils.distribution.choices_distribution_unique"
LOOP_BODY_FIRST_LINE = 45
TARGET_VALUE_LINE = 49
NTH = 2
VARIABLE = "uniform_sample"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/faker/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _parse_locals(line: str) -> dict[str, str]:
    idx = line.find(" locals=")
    if idx == -1:
        return {}
    raw = line[idx + len(" locals=") :].strip()
    try:
        value = ast.literal_eval(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _decode_value(raw: str):
    try:
        return ast.literal_eval(raw)
    except Exception:
        return raw


def extract_nth_iteration_value(trace_text: str) -> dict[str, object]:
    depth = 0
    iteration = 0

    for line in trace_text.splitlines():
        m = EVENT_RE.match(line)
        if not m:
            continue

        path = m.group("path")
        func = m.group("func")
        event = m.group("event")
        lineno = int(m.group("lineno"))

        if path != TARGET_PATH or func != TARGET_FUNC:
            continue

        if event == "call":
            depth += 1
            continue

        if event in {"return", "exception"}:
            depth = max(0, depth - 1)
            continue

        if event == "line" and depth == 1 and lineno == LOOP_BODY_FIRST_LINE:
            iteration += 1
            continue

        if (
            event == "line"
            and depth == 1
            and lineno == TARGET_VALUE_LINE
            and iteration == NTH
        ):
            locals_map = _parse_locals(line)
            if VARIABLE not in locals_map:
                raise ValueError(
                    f"Variable '{VARIABLE}' missing at iteration {NTH} on line {TARGET_VALUE_LINE}."
                )
            return {
                "nth_iteration": NTH,
                "variable": VARIABLE,
                "value": _decode_value(locals_map[VARIABLE]),
            }

    raise ValueError(f"Could not observe iteration {NTH} in top-level target loop.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/utils_choices_unique_nth_iteration_uniform_sample/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/utils_choices_unique_nth_iteration_uniform_sample/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_nth_iteration_value(trace_text)

    qa = {
        "question_kind": "iterations",
        "question": (
            "Use `faker_qa/utils_choices_unique_nth_iteration_uniform_sample/files/testcase.py`, class "
            "`TestUtilsChoicesUniqueNthIterationUniformSampleQA`, method "
            "`test_utils_choices_unique_nth_iteration_uniform_sample_case`. "
            "The test calls `seed_instance(31337007)` then "
            "`random_elements(OrderedDict([('x', 0.1), ('y', 0.2), ('z', 0.3), ('w', 0.4)]), length=2, unique=True)`, "
            "which uses weighted sampling without replacement via "
            "`faker.utils.distribution.choices_distribution_unique` "
            "(see `faker/utils/distribution.py`). "
            "In that function, consider the loop `for i in range(length):` at line `44` (loop body begins at line `45`). "
            "For the **2nd** iteration of that loop in the **top-level** invocation, "
            "after executing line `49` (`uniform_sample = random_sample(random=random)`), "
            "what is the exact value of local variable `uniform_sample`? "
            "Return a JSON object with exactly keys: `nth_iteration`, `variable`, `value`."
        ),
        "template_answer": {
            "nth_iteration": "int",
            "variable": "str",
            "value": "float",
        },
        "oracle_answer": answer,
        "execution": (
            "from collections import OrderedDict\n"
            "from faker import Faker\n"
            "fake = Faker()\n"
            "fake.seed_instance(31337007)\n"
            "fake.random_elements(\n"
            "    OrderedDict([('x', 0.1), ('y', 0.2), ('z', 0.3), ('w', 0.4)]),\n"
            "    length=2,\n"
            "    unique=True,\n"
            ")\n"
        ),
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
