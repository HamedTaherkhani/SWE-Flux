#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/libqtile/core/state\.py:(?P<lineno>\d+) "
    r"(?P<func>libqtile\.core\.state\.(?:QtileState\.)?apply) "
    r"event=exception exc=(?P<exc>[^:]+): ",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    seen = []
    for m in EXC_RE.finditer(trace_text):
        kind = m.group("exc").strip()
        if kind not in seen:
            seen.append(kind)

    if not seen:
        raise ValueError("Could not find exception events for QtileState.apply in trace log.")

    return {"caught_exception_kinds": seen}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "core_state_direct_apply_caught_exception_kinds/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "core_state_direct_apply_caught_exception_kinds/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "abnormal_behavior_prediction",
        "question": (
            "Use `tests/qa/core_state_direct_apply_caught_exception_kinds_test.py`, class "
            "`TestCoreStateDirectApplyCaughtExceptionKindsQA`, method "
            "`test_core_state_direct_apply_caught_exception_kinds_case`. "
            "This is a direct core test of `QtileState.apply` in `libqtile/core/state.py`. "
            "In this single run, `state.groups` is `[('g1', 'max', 'primary'), "
            "('missing_new', 'columns', 'created-by-except')]`, and `state.screens` is "
            "`{0: 'g1', 1: 'missing_group', 4: 'g1'}` for a qtile probe with exactly two screens "
            "and initial `groups_map={'g1': ...}`. `state.apply(qtile)` executes both internal "
            "`try/except` blocks that catch missing groups and invalid screen/group mappings. "
            "What are the exact kinds of exceptions that are caught internally during this test "
            "execution, in first-seen order?"
        ),
        "template_answer": {
            "caught_exception_kinds": ["str"]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
