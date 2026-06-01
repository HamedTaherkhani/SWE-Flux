#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TARGET_FUNC = "control.bdalg.feedback"
CONCRETE_FEEDBACK_FUNCS = {
    "control.frdata.feedback",
    "control.nlsys.feedback",
    "control.statesp.feedback",
    "control.xferfcn.feedback",
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

        if active_depth > 0 and event == "call" and func in CONCRETE_FEEDBACK_FUNCS:
            implementations.add((_relative_file(path), func))

        if active_depth > 0 and func == TARGET_FUNC and event in {"return", "exception"}:
            active_depth = max(0, active_depth - 1)

    if not implementations:
        raise ValueError("No concrete feedback implementations were observed.")

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
            "bdalg_feedback_dispatch_diversity_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "bdalg_feedback_dispatch_diversity_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_dispatch_diversity(trace_text)

    qa = {
        "question_kind": "M2_InterProceduralCFG",
        "question": (
            "Run the full test suite in "
            "`tests/qa/bdalg_feedback_dispatch_diversity_suite_test.py` "
            "(all test methods in its 10 test classes). The tests import the "
            "target directly with `from control.bdalg import feedback`. This "
            "is a dispatch-diversity question: identify which concrete "
            "`feedback` implementations are invoked by the top-level "
            "`control.bdalg.feedback` wrapper across the suite. Focus only on "
            "calls made while `control.bdalg.feedback` is active; this means "
            "the dynamic extent from each call to the wrapper until its "
            "matching return or exception, including nested calls, and taking "
            "the union over all tests. Do not include the wrapper "
            "`control.bdalg.feedback` itself. Report only concrete feedback "
            "method frames whose trace name is exactly one of "
            "`control.xferfcn.feedback`, `control.statesp.feedback`, "
            "`control.frdata.feedback`, or `control.nlsys.feedback`. Ignore "
            "helper conversion functions and calls from `control/tests`. For "
            "each dispatched implementation, use `file` as the forward-slash "
            "path relative to the repository root, such as `control/statesp.py`. "
            "Use `func` as `<module>.<code object name>`, where `<module>` is "
            "the function frame's module name and `<code object name>` is the "
            "Python code object's `co_name`; in this Python 3.10 environment, "
            "methods therefore appear without class names, for example "
            "`control.statesp.feedback`. Which unique concrete feedback "
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
