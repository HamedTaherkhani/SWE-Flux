#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# Trace plugin records every `event=line` for `format_text` (mod=
# yt_dlp.minicurses, co_name=format_text on Python 3.9).
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/minicurses\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.minicurses\.format_text) "
    r"event=line locals=\{.*\}$",
    re.MULTILINE,
)

BLOCK_LINES = {
    "block_at_line_50": 50,
    "block_at_line_64": 64,
}


def extract_reachability(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No format_text line events found in trace.")
    executed_lines = {int(m.group("lineno")) for m in matches}
    return {
        key: ("yes" if line in executed_lines else "no")
        for key, line in BLOCK_LINES.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/minicurses_format_text_block_reachability/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/minicurses_format_text_block_reachability/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_reachability(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/minicurses_format_text_block_reachability_test.py`, class "
            "`TestMinicursesFormatTextBlockReachabilityQA`, method "
            "`test_minicurses_format_text_block_reachability_case`. "
            "The test calls `yt_dlp.minicurses.format_text('Hello', FORMAT_SPEC)` (defined "
            "at line 33 in `yt_dlp/minicurses.py`) with the exact `FORMAT_SPEC` literal at "
            "the top of the test file: `'bold light red on cyan'`. "
            "Inside `format_text`, line 39 uppercases the format string and line 40 splits "
            "it into `tokens`. Line 43 (`if 'ON' in tokens:`) gates the BG-color block at "
            "lines 44-55, which pops the bg color and then conditionally applies a LIGHT "
            "modifier at lines 49-51 (`if tokens[-1] == 'LIGHT':` -> body lines 50-51). "
            "Independently, lines 57-69 process the FG color: line 62 pops the FG color, "
            "and then lines 63-65 conditionally apply a LIGHT modifier "
            "(`if tokens and tokens[-1] == 'LIGHT':` -> body lines 64-65). "
            "Critical mechanic: the order of `tokens.pop()` calls determines what "
            "`tokens[-1]` is at each `if tokens[-1] == 'LIGHT':` check. The BG block pops "
            "the bg color FIRST (line 48) and then checks `tokens[-1] == 'LIGHT'` AGAINST "
            "WHATEVER REMAINS, NOT against the original input. "
            "Report whether each of two specific block bodies is ever executed during this "
            "test run. Return a JSON object with these two keys -- each value must be the "
            "lowercase string `\"yes\"` or `\"no\"`: "
            "`block_at_line_50` -- whether the body of the BG-color LIGHT modifier "
            "(at line 50, `bg_color = f'0;10{bg_color[1:]}'`) is ever executed. "
            "`block_at_line_64` -- whether the body of the FG-color LIGHT modifier "
            "(at line 64, `fg_color = f'9{fg_color[1:]}'`) is ever executed."
        ),
        "template_answer": {
            "block_at_line_50": "yes_or_no",
            "block_at_line_64": "yes_or_no",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
