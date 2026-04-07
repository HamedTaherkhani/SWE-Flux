#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>[^ ]+) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = []
    for m in RETURN_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        func = m.group("func")
        if not path.endswith("/xarray/core/groupby.py"):
            continue
        if not func.endswith("._codes_to_group_indices"):
            continue
        matches.append(m)
    if not matches:
        raise ValueError("Could not find _codes_to_group_indices return event in trace log.")

    retval = ast.literal_eval(matches[-1].group("retval"))
    if not isinstance(retval, tuple):
        raise ValueError("Parsed retval is not a tuple.")
    if not all(isinstance(group, list) for group in retval):
        raise ValueError("Parsed retval groups are not all lists.")

    normalized = []
    for group in retval:
        for item in group:
            if not isinstance(item, int):
                raise ValueError("Group index contains non-integer item.")
        normalized.append(group)

    return {"group_indices": normalized}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/groupby_bins_indirect_function_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/groupby_bins_indirect_function_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `xarray/tests/qa/groupby_bins_indirect_function_output_test.py`, class "
            "`TestGroupByBinsIndirectFunctionOutputHardQA`, method "
            "`test_groupby_bins_indirect_function_output_case`. "
            "At line 19, `signal.groupby_bins(...)` is called with "
            "`score=[-4, -1, 0, 2, 6, 7, 11]` and `bins=[-2, 0, 3, 5, 10]`. "
            "This indirectly executes `xarray/core/groupby.py::_codes_to_group_indices` "
            "(line 71), invoked from `ResolvedGrouper.factorize` (around line 337). "
            "What is the exact return value of `_codes_to_group_indices` at line 77 "
            "for this execution? Return it as `group_indices`, preserving order and "
            "including empty groups."
        ),
        "template_answer": {
            "group_indices": "list[list[int]]"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
