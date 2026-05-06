#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.js_to_json) "
    r"event=return retval=(?P<retval>.*?) locals=\{.*\}$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> str:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No js_to_json return event in trace log.")
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly 1 js_to_json return event, got {len(matches)}.")

    retval_text = matches[0].group("retval")
    parsed = ast.literal_eval(retval_text)
    if not isinstance(parsed, str):
        raise ValueError(f"Return value is not a string: {parsed!r}")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/js_to_json_direct_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/js_to_json_direct_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/js_to_json_direct_output_test.py`, class "
            "`TestJsToJsonDirectOutputQA`, method `test_js_to_json_direct_output_case`. "
            "The test directly calls `yt_dlp.utils._utils.js_to_json(source_code)` "
            "(defined in `yt_dlp/utils/_utils.py` at line 2747) with the exact `source_code` "
            "Python raw string literal shown in the test (a JS-style object literal containing "
            "a leading `/* config */` block comment, a hex integer, a leading-zero octal "
            "integer, `undefined`, `void 0`, a double-quoted string with `\\x41`, a single-quoted "
            "string with `\\n`, `\\t`, `\\xFF`, a `new Date(\"...\")` call, a `parseInt(\"...\")` "
            "call, an `Array(...)` call, and a list with a trailing comma). The function is "
            "called with default `vars={}` and default `strict=False`, and is invoked exactly "
            "once (no recursive self-calls for this input). Report the exact string returned by "
            "this single `js_to_json` invocation, byte-for-byte (including any leading newline, "
            "internal newlines, escape sequences such as `\\u0041`, `\\u00FF`, `\\n`, `\\t`, and "
            "any whitespace). Return a JSON object with one key `output` whose value is the "
            "exact returned string."
        ),
        "template_answer": {
            "output": "str",
        },
        "oracle_answer": {
            "output": output,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
