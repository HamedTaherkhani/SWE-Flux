#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/font_manager\.py):(?P<lineno>\d+) "
    r"(?P<func>matplotlib\.font_manager\.score_family) event=line ",
    re.MULTILINE,
)


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for score_family execution path extraction.")

    executed_path = []
    for match in matches:
        executed_path.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": match.group("func"),
                "line": int(match.group("lineno")),
            }
        )

    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/font_manager_score_family_execution_path_multibranch/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/font_manager_score_family_execution_path_multibranch/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_execution_path(trace_text)

    qa = {
        "question_kind": "C1_IntraProceduralCFG",
        "question": (
            "Use `tests/qa/font_manager_score_family_execution_path_multibranch_test.py`, class "
            "`TestFontManagerScoreFamilyExecutionPathMultibranchQA`, method "
            "`test_font_manager_score_family_execution_path_multibranch_case`. "
            "The test issues four direct calls to `FontManager.score_family` on the global "
            "`fontManager` in this order: (1) `score_family((), 'DejaVu Sans')` (empty family tuple), "
            "(2) `score_family(['not_a_real_family_name', 'another_miss'], 'AlsoMissing')`, "
            "(3) `score_family(['sans-serif'], 'DejaVu Sans')` (generic alias list), "
            "(4) `score_family('DejaVu Sans', 'dejavu sans')` (scalar family string vs lowered name). "
            "Return the execution path only for file `lib/matplotlib/font_manager.py` and only for "
            "the function traced as `matplotlib.font_manager.score_family` (the `score_family` "
            "implementation). "
            "What is the exact ordered execution path as a list of objects with keys `file`, `func`, "
            "and `line`, including repeated lines?"
        ),
        "template_answer": {
            "executed_path": [
                {
                    "file": "str",
                    "func": "str",
                    "line": "int",
                }
            ]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
