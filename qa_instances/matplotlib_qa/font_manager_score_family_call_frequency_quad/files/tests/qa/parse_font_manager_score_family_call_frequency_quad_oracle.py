#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/font_manager\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call",
    re.MULTILINE,
)


def count_score_family_calls(trace_text: str) -> dict:
    """Count traced call events for FontManager.score_family."""
    n = 0
    for m in CALL_RE.finditer(trace_text):
        if m.group("func") == "matplotlib.font_manager.score_family":
            n += 1
    if n == 0:
        raise ValueError(
            "No traced calls for matplotlib.font_manager.score_family; "
            "check TRACE_FILE, TRACE_FUNC, and trace log path."
        )
    return {"function_call_count": n}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/font_manager_score_family_call_frequency_quad/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/font_manager_score_family_call_frequency_quad/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = count_score_family_calls(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `tests/qa/font_manager_score_family_call_frequency_quad_test.py`, class "
            "`TestFontManagerScoreFamilyCallFrequencyQuadQA`, method "
            "`test_font_manager_score_family_call_frequency_quad_case`. "
            "This test runs four `findfont` resolutions with distinct `FontProperties`: "
            "(1) five generic CSS families with bold/italic/expanded stretch, "
            "(2) monospace-first with numeric weight and oblique style, "
            "(3) mixed explicit and generic families with condensed stretch and relative size, "
            "(4) plain serif normal/normal. "
            "Generic lists expand through rcParams aliases; each candidate font is scored via "
            "`FontManager.score_family` alongside other scoring hooks. "
            "During the entire test run, how many times is "
            "`matplotlib.font_manager.FontManager.score_family` (traced as "
            "`matplotlib.font_manager.score_family`) in file `lib/matplotlib/font_manager.py` called?"
        ),
        "template_answer": {
            "function_call_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
