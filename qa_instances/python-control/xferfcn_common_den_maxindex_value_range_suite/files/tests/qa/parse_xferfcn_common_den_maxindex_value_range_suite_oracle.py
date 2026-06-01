#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


TARGET_FUNC = "control.xferfcn._common_den"
TARGET_FILE = "/testbed/control/xferfcn.py"
TARGET_LINE = 1102
TARGET_VARIABLE = "maxindex"

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/control/(?!tests/)[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
    r".*? locals=(?P<locals>\{.*\})$"
)


def extract_value_range(trace_text: str) -> dict:
    values: list[int] = []

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
        if TARGET_VARIABLE not in locals_dict:
            raise ValueError(
                f"Line {TARGET_LINE} did not contain local "
                f"{TARGET_VARIABLE!r}."
            )
        values.append(int(locals_dict[TARGET_VARIABLE]))

    if len(values) != 10:
        raise ValueError(
            f"Expected 10 observed {TARGET_VARIABLE!r} values at line "
            f"{TARGET_LINE}, observed {len(values)}: {values!r}."
        )

    return {
        "min_value": min(values),
        "max_value": max(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "xferfcn_common_den_maxindex_value_range_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "xferfcn_common_den_maxindex_value_range_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    answer = extract_value_range(Path(args.trace_log).read_text(encoding="utf-8"))

    qa = {
        "question_kind": "M4_ProgramState",
        "question": (
            "Run the full test suite in "
            "`tests/qa/xferfcn_common_den_maxindex_value_range_suite_test.py` "
            "(all 10 test methods in `TestCommonDenStateRangeQA`, in file "
            "order: `test_case_01`, `test_case_02`, `test_case_03`, "
            "`test_case_04`, `test_case_05`, `test_case_06`, `test_case_07`, "
            "`test_case_08`, `test_case_09`, and `test_case_10`). The tests "
            "import the constructor directly with `from control.xferfcn import "
            "tf` and then call `TransferFunction._common_den()` on the "
            "constructed systems. Focus on the local variable `maxindex` inside "
            "`control.xferfcn._common_den`. It is assigned on line 1101 as "
            "`maxindex = max([len(p) for p in poles])` after poles have been "
            "collected and merged per input, and its value is visible at line "
            "1102, `den = zeros((self.ninputs, maxindex + 1), dtype=float)`. "
            "Across all executions of line 1102 caused by this suite, what "
            "are the minimum and maximum values reached by `maxindex`? Return "
            "only `min_value` and `max_value` as numbers."
        ),
        "template_answer": {
            "min_value": "int",
            "max_value": "int",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(
        json.dumps(qa, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
