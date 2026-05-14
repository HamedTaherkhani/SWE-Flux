#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>[^ ]+) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_profile(trace_text: str) -> dict[str, dict[str, str]]:
    matches = []
    for m in RETURN_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        func = m.group("func")
        if not path.endswith("/xarray/tests/qa/pandasindex_incompatible_inputs_profile_test.py"):
            continue
        if not func.endswith(".test_pandasindex_incompatible_inputs_profile_case"):
            continue
        matches.append(m)
    if not matches:
        raise ValueError("Could not find target test return event in trace log.")

    locals_map = ast.literal_eval(matches[-1].group("locals"))
    if not isinstance(locals_map, dict):
        raise ValueError("Parsed locals map is not a dict.")

    required = {
        "case_one_exception_kind",
        "case_one_exception_message",
        "case_two_exception_kind",
        "case_two_exception_message",
    }
    missing = required - set(locals_map)
    if missing:
        raise ValueError(f"Missing expected locals in trace: {sorted(missing)}")

    one_kind = ast.literal_eval(locals_map["case_one_exception_kind"])
    one_msg = ast.literal_eval(locals_map["case_one_exception_message"])
    two_kind = ast.literal_eval(locals_map["case_two_exception_kind"])
    two_msg = ast.literal_eval(locals_map["case_two_exception_message"])

    if not all(isinstance(v, str) for v in (one_kind, one_msg, two_kind, two_msg)):
        raise ValueError("Expected all extracted fields to be strings.")

    return {
        "case_method_type_mismatch": {
            "exception_kind": one_kind,
            "exception_message": one_msg,
        },
        "case_label_dict_like_mismatch": {
            "exception_kind": two_kind,
            "exception_message": two_msg,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/pandasindex_incompatible_inputs_profile/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/pandasindex_incompatible_inputs_profile/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_profile(trace_text)

    qa = {
        "question_kind": "C6_Exceptions",
        "question": (
            "Use `xarray/tests/qa/pandasindex_incompatible_inputs_profile_test.py`, class "
            "`TestPandasIndexIncompatibleInputsProfileHardQA`, method "
            "`test_pandasindex_incompatible_inputs_profile_case`. "
            "In this test, `xarray/core/indexes.py::PandasIndex.sel` is executed in two incompatible-input cases: "
            "(1) `method=7` (non-string) with labels `{'x': 2}`, and "
            "(2) dict-like label `{'x': {'left': 2}}` with default method. "
            "For each case, what exception kind and exact exception message are produced?"
        ),
        "template_answer": {
            "case_method_type_mismatch": {
                "exception_kind": "str",
                "exception_message": "str",
            },
            "case_label_dict_like_mismatch": {
                "exception_kind": "str",
                "exception_message": "str",
            },
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
