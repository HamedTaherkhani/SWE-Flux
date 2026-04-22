#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/backend/base/drawer\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.backend\.base\.drawer\.(?:TextFrame\.)?draw) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find TextFrame.draw return events in trace log.")

    # The test calls draw() three times; target is the final call.
    target = matches[-1]
    locals_dict = ast.literal_eval(target.group("locals"))

    opts_raw = locals_dict.get("opts")
    if opts_raw is None:
        raise ValueError("Missing local variable `opts` at TextFrame.draw return.")

    opts = ast.literal_eval(str(opts_raw))
    if not (isinstance(opts, list) and len(opts) == 5):
        raise ValueError("Expected `opts` to be a list of five integers.")

    return {"variable_state": {"opts": [int(v) for v in opts]}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "backend_textframe_direct_draw_conditional_opts_state/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "backend_textframe_direct_draw_conditional_opts_state/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/backend_textframe_direct_draw_conditional_opts_state_test.py`, class "
            "`TestBackendTextFrameDirectDrawConditionalOptsStateQA`, method "
            "`test_backend_textframe_direct_draw_conditional_opts_state_case`. "
            "This is a direct backend test of `TextFrame.draw` in "
            "`libqtile/backend/base/drawer.py`. The test creates a `TextFrame` with "
            "`border_width=7`, `pad_x=(11, 4)`, `pad_y=(8, 5)`, does two warm-up `draw` calls, "
            "then calls `frame.draw(37, 23, rounded=False, fill=False, line=True, highlight=True)`. "
            "In that final call, the code enters the nested `if line:` and `if highlight:` branches "
            "and mutates local variable `opts` before return. What is the exact final value of `opts`?"
        ),
        "template_answer": {"variable_state": {"opts": ["int", "int", "int", "int", "int"]}},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
