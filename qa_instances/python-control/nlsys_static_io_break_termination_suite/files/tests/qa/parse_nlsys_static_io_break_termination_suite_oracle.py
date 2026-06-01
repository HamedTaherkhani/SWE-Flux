#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TARGET_FUNC = "control.nlsys._compute_static_io"
TARGET_FILE = "/testbed/control/nlsys.py"
BREAK_LINE = 986

TEST_ORDER = [
    "TestStaticIOTerminationQA::test_case_01",
    "TestStaticIOTerminationQA::test_case_02",
    "TestStaticIOTerminationQA::test_case_03",
    "TestStaticIOTerminationQA::test_case_04",
    "TestStaticIOTerminationQA::test_case_05",
    "TestStaticIOTerminationQA::test_case_06",
    "TestStaticIOTerminationQA::test_case_07",
    "TestStaticIOTerminationQA::test_case_08",
    "TestStaticIOTerminationQA::test_case_09",
    "TestStaticIOTerminationQA::test_case_10",
]

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/control/(?!tests/)[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
)


def extract_break_tests(trace_text: str) -> dict:
    active_depth = 0
    current_hit_break = False
    break_flags: list[bool] = []

    for raw_line in trace_text.splitlines():
        match = TRACE_RE.match(raw_line)
        if not match:
            continue

        path = match.group("path")
        lineno = int(match.group("lineno"))
        func = match.group("func")
        event = match.group("event")

        if event == "call" and func == TARGET_FUNC:
            active_depth += 1
            if active_depth == 1:
                current_hit_break = False
            continue

        if active_depth > 0 and event == "line":
            if path == TARGET_FILE and func == TARGET_FUNC and lineno == BREAK_LINE:
                current_hit_break = True

        if active_depth > 0 and func == TARGET_FUNC and event in {"return", "exception"}:
            active_depth = max(0, active_depth - 1)
            if active_depth == 0:
                break_flags.append(current_hit_break)
                current_hit_break = False

    if len(break_flags) != len(TEST_ORDER):
        raise ValueError(
            f"Expected {len(TEST_ORDER)} _compute_static_io invocations, "
            f"observed {len(break_flags)}."
        )

    return {
        "tests_terminating_at_break": [
            test_id for test_id, hit_break in zip(TEST_ORDER, break_flags)
            if hit_break
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "nlsys_static_io_break_termination_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "nlsys_static_io_break_termination_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    answer = extract_break_tests(Path(args.trace_log).read_text(encoding="utf-8"))

    qa = {
        "question_kind": "M3_Loops",
        "question": (
            "Run the full test suite in "
            "`tests/qa/nlsys_static_io_break_termination_suite_test.py` "
            "(all 10 test methods in `TestStaticIOTerminationQA`, in file "
            "order: `test_case_01`, `test_case_02`, `test_case_03`, "
            "`test_case_04`, `test_case_05`, `test_case_06`, `test_case_07`, "
            "`test_case_08`, `test_case_09`, and `test_case_10`). The "
            "tests import the constructors directly with `from control.nlsys "
            "import interconnect, nlsys` and then call `_compute_static_io` on "
            "the constructed interconnected systems. Focus on the "
            "static-feedthrough propagation loop in `control/nlsys.py` inside "
            "`control.nlsys._compute_static_io`: the loop header is line 958, "
            "`while cycle_count > 0:`. The specific termination statement of "
            "interest is the `break` on line 986, reached when "
            "`(ulist == new_ulist).all()` is true. Some tests instead exhaust "
            "`cycle_count` and raise `RuntimeError(\"algebraic loop detected\")`; "
            "those do not terminate at the break. Which tests cause this "
            "specific loop invocation to terminate at the break statement on "
            "line 986? Return `tests_terminating_at_break` as a list of "
            "strings using the format `ClassName::test_method`, preserving "
            "the test file order."
        ),
        "template_answer": {
            "tests_terminating_at_break": ["str"],
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
