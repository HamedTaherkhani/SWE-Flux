#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/reflex/style\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)

ALLOWED_FUNCS = {
    "reflex.style.convert_dict_to_style_and_format_emotion",
    "reflex.style.Style.__init__",
    "reflex.style.Style.update",
    "reflex.style.Style.__setitem__",
    "reflex.style.convert",
    "reflex.style.convert_list",
    "reflex.style.convert_item",
    "reflex.style.format_style_key",
    "reflex.style.format_as_emotion",
    "reflex.style._format_emotion_style_pseudo_selector",
    "reflex.style.media_query",
}


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for execution path extraction.")

    executed_path = []
    for match in matches:
        func = match.group("func")
        if func not in ALLOWED_FUNCS:
            continue
        executed_path.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": func,
                "line": int(match.group("lineno")),
            }
        )
    if not executed_path:
        raise ValueError("Trace had line events, but none matched the exact target functions.")
    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/style_emotion_format_execution_path_lines/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/style_emotion_format_execution_path_lines/oracle.json",
    )
    args = parser.parse_args()

    output = extract_execution_path(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/style_emotion_format_execution_path_lines_test.py`, class "
            "`TestStyleEmotionFormatExecutionPathLinesQA`, method "
            "`test_style_emotion_format_execution_path_lines_case`. The `raw_style` dictionary is constructed "
            "at lines 8-16, and line 18 calls `convert_dict_to_style_and_format_emotion(raw_style)`. "
            "Return the execution path only for line events in `reflex/style.py`, and only for these functions: "
            "`reflex.style.convert_dict_to_style_and_format_emotion`, `reflex.style.Style.__init__`, "
            "`reflex.style.Style.update`, `reflex.style.Style.__setitem__`, `reflex.style.convert`, "
            "`reflex.style.convert_list`, `reflex.style.convert_item`, `reflex.style.format_style_key`, "
            "`reflex.style.format_as_emotion`, `reflex.style._format_emotion_style_pseudo_selector`, and "
            "`reflex.style.media_query`. This execution converts shorthand keys, nested pseudo-selector styles, "
            "responsive lists, and a CSS custom property into the Emotion style representation. What is the exact "
            "ordered execution path as a list of objects with keys `file`, `func`, and `line`, including repeated lines?"
        ),
        "template_answer": {
            "executed_path": [{"file": "str", "func": "str", "line": "int"}]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
