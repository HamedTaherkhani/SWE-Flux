#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# Trace plugin records every `event=call` in /testbed/yt_dlp/webvtt.py during
# the test. On Python 3.9 there is no `co_qualname`, so the trace shows the
# bare `co_name` (no class prefix); the line number disambiguates which class
# each `__init__` (or other shared name) belongs to.
CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/webvtt\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.webvtt\.\S+) "
    r"event=call locals=\{.*\}$",
    re.MULTILINE,
)


def extract_call_order(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No call events found in trace.")

    function_call_order = []
    for m in matches:
        bare_name = m.group("func").rsplit(".", 1)[1]
        function_call_order.append({
            "file": "yt_dlp/webvtt.py",
            "func": bare_name,
            "line": int(m.group("lineno")),
        })
    return {
        "function_call_order": function_call_order,
        "function_call_count": len(function_call_order),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/webvtt_magic_parse_function_call_order/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/webvtt_magic_parse_function_call_order/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_order(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/webvtt_magic_parse_function_call_order_test.py`, class "
            "`TestWebvttMagicParseFunctionCallOrderQA`, method "
            "`test_webvtt_magic_parse_function_call_order_case`. "
            "The test does exactly two things: "
            "(1) constructs `parser = _MatchParser(WEBVTT_INPUT)` and "
            "(2) calls `Magic.parse(parser)` (defined at line 199 in "
            "`yt_dlp/webvtt.py`), with the exact `WEBVTT_INPUT` literal at the top of the "
            "test file: `'WEBVTT - sample\\nKind: captions\\nLanguage: en\\n\\n'`. "
            "List every Python function CALL that occurs inside `yt_dlp/webvtt.py` during "
            "this test, in order. Notes you must rely on: "
            "(a) `_MatchParser.consume(r)` (line 50) is `return self.advance(self.match(r))`, "
            "which always calls `match` (line 27) AND ALWAYS calls `advance` (line 36) -- "
            "even when `match` returned `None`, because Python evaluates `self.match(r)` and "
            "passes the result to `self.advance(...)` regardless. "
            "(b) `_MatchParser.child()` (line 53) constructs a `_MatchChildParser` whose "
            "`__init__` (line 65) calls `super().__init__(parent._data)`, i.e. "
            "`_MatchParser.__init__` (line 23). "
            "(c) `Magic.parse` (line 199) returns `cls(extra=..., mpegts=..., local=..., "
            "meta=...)`, which dispatches to `Block.__init__` (line 122) since `Magic` "
            "inherits from `HeaderBlock` -> `Block` and does not define its own `__init__`. "
            "(d) Magic's outer while-loop terminates only when `parser.consume(_REGEX_NL)` "
            "matches a blank line. (e) On Python 3.9 the trace plugin shows the bare "
            "`co_name` (e.g. `__init__`, `parse`, `consume`); the line number "
            "disambiguates which class each `__init__` belongs to. "
            "Return a JSON object with two keys: "
            "`function_call_order` -- a list of objects each shaped exactly as "
            "`{\"file\": \"yt_dlp/webvtt.py\", \"func\": <bare_co_name>, "
            "\"line\": <int>}`, in the order of every `event=call` for "
            "`yt_dlp/webvtt.py` during the test, including repeats; and "
            "`function_call_count` (int, the length of that list)."
        ),
        "template_answer": {
            "function_call_order": [
                {"file": "str", "func": "str", "line": "int"},
            ],
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
