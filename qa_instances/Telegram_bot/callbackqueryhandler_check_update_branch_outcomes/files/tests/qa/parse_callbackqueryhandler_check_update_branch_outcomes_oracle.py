#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/telegram/ext/_handlers/callbackqueryhandler.py"
TARGET_FUNC = "telegram.ext._handlers.callbackqueryhandler.CallbackQueryHandler.check_update"

CONDITION_SPECS = [
    (164, 165),
    (170, 171),
    (175, 176),
    (176, 177),
    (178, 179),
    (180, 181),
    (182, 183),
    (184, 185),
    (187, 188),
    (188, 189),
    (190, 191),
]

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
)


def _load_condition_texts() -> dict[int, str]:
    source = Path(TARGET_PATH).read_text(encoding="utf-8").splitlines()
    return {line_no: source[line_no - 1].strip() for line_no, _ in CONDITION_SPECS}


def _extract_top_level_call_lines(trace_text: str) -> list[list[int]]:
    depth = 0
    current: list[int] = []
    calls: list[list[int]] = []

    for raw in trace_text.splitlines():
        match = EVENT_RE.match(raw)
        if not match:
            continue

        if match.group("path") != TARGET_PATH or match.group("func") != TARGET_FUNC:
            continue

        event = match.group("event")
        lineno = int(match.group("lineno"))

        if event == "call":
            depth += 1
            if depth == 1:
                current = []
            continue

        if event == "line" and depth == 1:
            current.append(lineno)
            continue

        if event in {"return", "exception"}:
            if depth == 1:
                calls.append(current)
                current = []
            depth = max(0, depth - 1)

    return calls


def _condition_outcomes_in_call(lines: list[int], cond_line: int, true_line: int) -> list[str]:
    outcomes: list[str] = []
    for idx, value in enumerate(lines):
        if value != cond_line:
            continue
        next_line = lines[idx + 1] if idx + 1 < len(lines) else None
        outcomes.append("true" if next_line == true_line else "false")
    return outcomes


def extract_condition_branches(trace_text: str) -> list[dict[str, object]]:
    calls = _extract_top_level_call_lines(trace_text)
    cond_texts = _load_condition_texts()

    results: list[dict[str, object]] = []
    for cond_line, true_line in CONDITION_SPECS:
        seen: set[str] = set()
        for call_lines in calls:
            seen.update(_condition_outcomes_in_call(call_lines, cond_line, true_line))

        if not seen:
            continue

        ordered = [value for value in ("false", "true") if value in seen]
        results.append(
            {
                "line": cond_line,
                "condition": cond_texts[cond_line],
                "branches_executed": ordered,
            }
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "callbackqueryhandler_check_update_branch_outcomes/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "callbackqueryhandler_check_update_branch_outcomes/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    condition_branches = extract_condition_branches(trace_text)

    qa = {
        "question_kind": "C1_IntraProceduralCFG",
        "question": (
            "Run only `tests/qa/callbackqueryhandler_check_update_branch_outcomes_test.py::"
            "TestCallbackQueryHandlerCheckUpdateBranchOutcomesQA::"
            "test_callbackqueryhandler_check_update_branch_outcomes_case`. "
            "Focus on `telegram/ext/_handlers/callbackqueryhandler.py`, function "
            "`telegram.ext._handlers.callbackqueryhandler.CallbackQueryHandler.check_update`. "
            "For each evaluated condition line in this function, report which branch outcomes "
            "were executed under this test. In `branches_executed`, use `true` if that "
            "condition evaluated to true at least once (so execution entered the `if` block "
            "body for that line), and use `false` if that condition evaluated to false at "
            "least once (so execution followed the non-`if` path). If both happened across "
            "different evaluations of the same line, include both values. "
            "Return a JSON object with key `condition_branches` whose value is an array of "
            "objects in ascending line-number order, each object using this exact schema: "
            "`{\"line\": <int>, \"condition\": <exact condition source text>, "
            "\"branches_executed\": [\"false\" and/or \"true\"]}`. "
            "Include only condition lines that were evaluated at least once."
        ),
        "template_answer": {
            "condition_branches": [],
        },
        "oracle_answer": {
            "condition_branches": condition_branches,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
