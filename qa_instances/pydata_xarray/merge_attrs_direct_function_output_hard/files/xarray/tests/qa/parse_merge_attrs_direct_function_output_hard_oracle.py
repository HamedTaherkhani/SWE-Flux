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
        func = m.group("func")
        if not func.endswith(".merge_attrs"):
            continue
        matches.append(m)
    if not matches:
        raise ValueError("Could not find merge_attrs return event in trace log.")

    retval = ast.literal_eval(matches[-1].group("retval"))
    if not isinstance(retval, dict):
        raise ValueError("Parsed retval is not a dict.")
    return {"merged_attrs": retval}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/merge_attrs_direct_function_output_hard/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/merge_attrs_direct_function_output_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `xarray/tests/qa/merge_attrs_direct_function_output_hard_test.py`, class "
            "`TestMergeAttrsDirectFunctionOutputHardQA`, method "
            "`test_merge_attrs_direct_function_output_hard_case`. "
            "At line 31, the test directly calls `xarray/core/merge.py::merge_attrs` "
            "with `combine_attrs='drop_conflicts'` and exactly these input dicts in order: "
            "`{'units': 'm', 'source': 'sensorA', 'qc': ('ok', 1), 'scale': 1, 'tag': 'x'}`, "
            "`{'units': 'm', 'source': 'sensorB', 'qc': ('ok', 1), 'scale': 1, 'new': 5, 'tag': 'x'}`, "
            "`{'units': 'cm', 'qc': ('ok', 2), 'new': 5, 'tag': 'x', 'note': 'v3'}`. "
            "What is the exact returned dictionary at line 605? Return it as `merged_attrs`."
        ),
        "template_answer": {
            "merged_attrs": "dict[str, object]"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
