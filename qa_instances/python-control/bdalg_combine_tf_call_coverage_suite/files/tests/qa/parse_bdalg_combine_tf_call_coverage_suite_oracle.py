#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TARGET_FUNC = "control.bdalg.combine_tf"
INCLUDED_PREFIXES = (
    "control.bdalg.",
    "control.xferfcn.",
    "control.iosys.",
    "control.lti.",
    "control.config.",
)

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/control/(?!tests/)[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|return|exception)\b"
)


def _relative_file(path: str) -> str:
    return path.replace("/testbed/", "")


def extract_call_coverage(trace_text: str) -> dict:
    active_depth = 0
    covered: set[tuple[str, str]] = set()

    for raw_line in trace_text.splitlines():
        match = CALL_RE.match(raw_line)
        if not match:
            continue

        func = match.group("func")
        event = match.group("event")
        path = match.group("path")

        if event == "call" and func == TARGET_FUNC:
            active_depth += 1
            covered.add((_relative_file(path), func))
            continue

        if active_depth > 0 and event == "call":
            if func.startswith(INCLUDED_PREFIXES) and "<" not in func:
                covered.add((_relative_file(path), func))

        if active_depth > 0 and func == TARGET_FUNC and event in {"return", "exception"}:
            active_depth = max(0, active_depth - 1)

    if not covered:
        raise ValueError("No call events were collected while combine_tf was active.")

    return {
        "covered_functions": [
            {"file": file, "func": func}
            for file, func in sorted(covered, key=lambda item: (item[0], item[1]))
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "bdalg_combine_tf_call_coverage_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "bdalg_combine_tf_call_coverage_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_call_coverage(trace_text)

    qa = {
        "question_kind": "M2_InterProceduralCFG",
        "question": (
            "Run the full test suite in "
            "`tests/qa/bdalg_combine_tf_call_coverage_suite_test.py` "
            "(all test methods in its 10 test classes). The tests import the "
            "target directly with `from control.bdalg import combine_tf`. Focus "
            "on calls made while `control.bdalg.combine_tf` is active; this "
            "means the dynamic extent from each call to `combine_tf` until its "
            "matching return or exception, including nested calls made by "
            "`combine_tf`, and taking the union over all tests. Include "
            "`control.bdalg.combine_tf` itself. Within that dynamic extent, "
            "consider only functions whose trace names start with one of "
            "`control.bdalg.`, `control.xferfcn.`, `control.iosys.`, "
            "`control.lti.`, or `control.config.`, and ignore calls from "
            "`control/tests`. Exclude generated code-object names containing "
            "angle brackets, such as `<listcomp>`, `<genexpr>`, and `<lambda>`. "
            "For each covered function, use `file` as the forward-slash path "
            "relative to the repository root, such as `control/bdalg.py`. Use "
            "`func` as `<module>.<code object name>`, where `<module>` is the "
            "function frame's module name and `<code object name>` is the Python "
            "code object's `co_name`; in this Python 3.10 environment, methods "
            "therefore appear without class names, for example "
            "`control.xferfcn.__init__`. Which unique functions are covered at "
            "least once by this suite? Return `covered_functions` as a list of "
            "objects with keys `file` and `func`, sorted by `file` and then `func`."
        ),
        "template_answer": {
            "covered_functions": [
                {
                    "file": "str",
                    "func": "str",
                }
            ]
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
