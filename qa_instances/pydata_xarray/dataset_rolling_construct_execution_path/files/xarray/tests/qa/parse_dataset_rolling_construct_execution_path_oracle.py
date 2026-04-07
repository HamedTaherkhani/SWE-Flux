#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>[^ ]+) "
    r"event=line ",
    re.MULTILINE,
)

TARGET_FUNCTION_IDENTIFIER = (
    "xarray.computation.rolling.construct|||"
    "xarray/core/rolling.py::DatasetRolling.construct|||"
    "DatasetRolling.construct|||construct"
)


def _iter_identifier_tokens(func: str) -> list[str]:
    if "|||" in func:
        return [part.strip() for part in func.split("|||") if part.strip()]
    return [func.strip()]


def _short_name(func_token: str) -> str:
    rhs = func_token.split("::", 1)[-1]
    return rhs.rsplit(".", 1)[-1]


def extract_execution_path(trace_text: str) -> dict[str, list[dict[str, int | str]]]:
    path = []
    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not any(_short_name(token) == "construct" for token in _iter_identifier_tokens(func)):
            continue
        path.append(
            {
                "file": "xarray/core/rolling.py",
                "func": TARGET_FUNCTION_IDENTIFIER,
                "line": int(m.group("lineno")),
            }
        )

    if not path:
        raise ValueError("Could not find DatasetRolling.construct line events in trace log.")

    return {"executed_path": path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/dataset_rolling_construct_execution_path/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/dataset_rolling_construct_execution_path/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_execution_path(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `xarray/tests/qa/dataset_rolling_construct_execution_path_test.py`, class "
            "`TestDatasetRollingConstructExecutionPathHardQA`, method "
            "`test_dataset_rolling_construct_execution_path_case`. "
            "At line 31, `ds.rolling(x=3, center=True).construct(window_dim='win', stride=2, "
            "fill_value=-1, keep_attrs=False)` is called. Focus only on function "
            "`xarray/core/rolling.py::DatasetRolling.construct`. "
            "What is the exact ordered execution path inside this function, including repeated line "
            "visits from loop iterations and branch checks? Return it as `executed_path`, a list of "
            "objects with keys `file`, `func`, and `line`."
        ),
        "template_answer": {
            "executed_path": [
                {"file": "str", "func": "str", "line": "int"}
            ]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
