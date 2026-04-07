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


def extract_exception_profile(trace_text: str) -> dict[str, str]:
    matches = []
    for m in RETURN_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        func = m.group("func")
        if not path.endswith("/xarray/tests/qa/isdtype_kind_exception_profile_test.py"):
            continue
        if not func.endswith(".test_isdtype_kind_exception_profile_case"):
            continue
        matches.append(m)

    if not matches:
        raise ValueError("Could not find target test return event in trace log.")

    locals_map = ast.literal_eval(matches[-1].group("locals"))
    required = {
        "expected_exception_kind",
        "observed_exception_kind",
        "observed_exception_message",
    }
    missing = required - set(locals_map)
    if missing:
        raise ValueError(f"Missing expected locals in trace: {sorted(missing)}")

    expected_kind = ast.literal_eval(locals_map["expected_exception_kind"])
    observed_kind = ast.literal_eval(locals_map["observed_exception_kind"])
    observed_message = ast.literal_eval(locals_map["observed_exception_message"])

    return {
        "expected_exception_kind": expected_kind,
        "observed_exception_kind": observed_kind,
        "observed_exception_message": observed_message,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/isdtype_kind_exception_profile/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/isdtype_kind_exception_profile/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_exception_profile(trace_text)

    qa = {
        "question_kind": "abnormal_behavior_prediction",
        "question": (
            "Use `xarray/tests/qa/isdtype_kind_exception_profile_test.py`, class "
            "`TestIsDtypeKindExceptionProfileHardQA`, method "
            "`test_isdtype_kind_exception_profile_case`. Inside this test, the call to "
            "`xarray/core/dtypes.py::isdtype(np.dtype('int64'), 123)` throws an uncaught exception "
            "that the test captures with `pytest.raises(...)`. What are (1) the expected exception "
            "kind used by the test expectation, (2) the observed exception kind, and (3) the exact "
            "observed exception message string?"
        ),
        "template_answer": {
            "expected_exception_kind": "str",
            "observed_exception_kind": "str",
            "observed_exception_message": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
