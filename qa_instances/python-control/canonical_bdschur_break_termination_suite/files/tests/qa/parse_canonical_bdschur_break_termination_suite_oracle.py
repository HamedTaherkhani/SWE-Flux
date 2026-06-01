#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TARGET_FUNC = "control.canonical._bdschur_condmax_search"
TARGET_FILE = "/testbed/control/canonical.py"
BREAK_LINE = 374

TEST_ORDER = [
    "TestCanonicalSearchTerminationQA::test_case_01",
    "TestCanonicalSearchTerminationQA::test_case_02",
    "TestCanonicalSearchTerminationQA::test_case_03",
    "TestCanonicalSearchTerminationQA::test_case_04",
    "TestCanonicalSearchTerminationQA::test_case_05",
    "TestCanonicalSearchTerminationQA::test_case_06",
    "TestCanonicalSearchTerminationQA::test_case_07",
    "TestCanonicalSearchTerminationQA::test_case_08",
    "TestCanonicalSearchTerminationQA::test_case_09",
    "TestCanonicalSearchTerminationQA::test_case_10",
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
            f"Expected {len(TEST_ORDER)} _bdschur_condmax_search invocations, "
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
            "canonical_bdschur_break_termination_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "canonical_bdschur_break_termination_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    answer = extract_break_tests(Path(args.trace_log).read_text(encoding="utf-8"))

    qa = {
        "question_kind": "M3_Loops",
        "question": (
            "Run the full test suite in "
            "`tests/qa/canonical_bdschur_break_termination_suite_test.py` "
            "(all 10 test methods in `TestCanonicalSearchTerminationQA`, in "
            "file order: `test_case_01`, `test_case_02`, `test_case_03`, "
            "`test_case_04`, `test_case_05`, `test_case_06`, `test_case_07`, "
            "`test_case_08`, `test_case_09`, and `test_case_10`). The tests "
            "import the target directly with `from control.canonical import "
            "_bdschur_condmax_search` and install a deterministic fake "
            "`slycot.mb03rd` before each call. Focus on the phase-1 search "
            "loop in `control/canonical.py` inside "
            "`control.canonical._bdschur_condmax_search`: the loop header is "
            "line 364, `for i in range(50):`. The specific termination "
            "statement of interest is the `break` on line 374, reached when "
            "the computed condition number is not less than `condmax` and "
            "the function records an upper bound before entering phase 2. "
            "Tests that return from inside the loop or fall through the "
            "loop's `else` clause do not terminate at this break. Which "
            "tests cause this specific loop invocation to terminate at the "
            "break statement on line 374? Return "
            "`tests_terminating_at_break` as a list of strings using the "
            "format `ClassName::test_method`, preserving the test file order."
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
