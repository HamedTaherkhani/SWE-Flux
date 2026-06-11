#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TARGET_FUNC = "control.bdalg.append"
CONCRETE_APPEND_FUNCS = {
    "control.frdata.append",
    "control.statesp.append",
    "control.xferfcn.append",
}

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/control/(?!tests/)[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|return|exception)\b"
)


def _relative_file(path: str) -> str:
    return path.replace("/testbed/", "")


def extract_dispatch_diversity(trace_text: str) -> dict:
    active_depth = 0
    implementations: set[tuple[str, str]] = set()

    for raw_line in trace_text.splitlines():
        match = CALL_RE.match(raw_line)
        if not match:
            continue

        func = match.group("func")
        event = match.group("event")
        path = match.group("path")

        if event == "call" and func == TARGET_FUNC:
            active_depth += 1
            continue

        if active_depth > 0 and event == "call" and func in CONCRETE_APPEND_FUNCS:
            implementations.add((_relative_file(path), func))

        if active_depth > 0 and func == TARGET_FUNC and event in {"return", "exception"}:
            active_depth = max(0, active_depth - 1)

    if not implementations:
        raise ValueError("No concrete append implementations were observed.")

    return {
        "dispatched_implementations": [
            {"file": file, "func": func}
            for file, func in sorted(
                implementations, key=lambda item: (item[0], item[1])
            )
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "bdalg_append_dispatch_diversity_subset_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "bdalg_append_dispatch_diversity_subset_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_dispatch_diversity(trace_text)

    qa = {
        "question_kind": "M6_InterProceduralCFG",
        "question": (
            "Run the full test suite in "
            "`tests/qa/bdalg_append_dispatch_diversity_subset_suite_test.py` "
            "(all test methods in its 10 test classes). The tests import the "
            "target directly with `from control.bdalg import append`. This is "
            "a dispatch-diversity question: identify which concrete `append` "
            "implementations are invoked by the top-level "
            "`control.bdalg.append` wrapper across the suite. Focus only on "
            "calls made while `control.bdalg.append` is active; this means the "
            "dynamic extent from each call to the wrapper until its matching "
            "return or exception, including nested calls, and taking the union "
            "over all tests. Do not include the wrapper `control.bdalg.append` "
            "itself. Report only concrete append method frames whose trace "
            "name is exactly one of `control.xferfcn.append`, "
            "`control.statesp.append`, or `control.frdata.append`. The suite "
            "is not guaranteed to invoke every concrete implementation in "
            "that candidate set, so do not include an implementation unless "
            "it is actually called by these tests. Ignore helper conversion "
            "functions and calls from `control/tests`. For each dispatched "
            "implementation, use `file` as the forward-slash path relative to "
            "the repository root, such as `control/frdata.py`. Use `func` as "
            "`<module>.<code object name>`, where `<module>` is the function "
            "frame's module name and `<code object name>` is the Python code "
            "object's `co_name`; in this Python 3.10 environment, methods "
            "therefore appear without class names, for example "
            "`control.frdata.append`. Which unique concrete append "
            "implementations are invoked at least once by this suite? Return "
            "`dispatched_implementations` as a list of objects with keys "
            "`file` and `func`, sorted by `file` and then `func`."
        ),
        "template_answer": {
            "dispatched_implementations": [
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
