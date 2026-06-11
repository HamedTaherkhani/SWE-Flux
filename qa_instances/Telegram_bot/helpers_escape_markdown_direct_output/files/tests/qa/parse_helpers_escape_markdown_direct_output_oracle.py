#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/helpers\.py):(?P<lineno>\d+) "
    r"(?P<func>telegram\.helpers\.escape_markdown) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> str:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find escape_markdown return events in trace log.")

    target = matches[-1]
    retval = target.group("retval")
    parsed = ast.literal_eval(retval)
    if not isinstance(parsed, str):
        raise ValueError("Parsed return value is not a string.")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/helpers_escape_markdown_direct_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/helpers_escape_markdown_direct_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/helpers_escape_markdown_direct_output_test.py`, class "
            "`TestHelpersEscapeMarkdownDirectOutputQA`, method "
            "`test_escape_markdown_direct_output_case`. "
            "This test directly calls `telegram/helpers.py::escape_markdown` (line 45) with "
            "`source_text=r'A_B[C](D)~E`F>G#H+I-J=K|L{M}.N! and slash \\\\ end'` and "
            "`version=2`. In that function, `escape_chars` is chosen in lines 67-73 and "
            "line 77 returns `re.sub(...)`. What exact string is returned at line 77?"
        ),
        "template_answer": {"output": "str"},
        "oracle_answer": {"output": output},
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
