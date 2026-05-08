#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# Trace plugin records every `event=call` for any frame inside
# /testbed/yt_dlp/webvtt.py. On Python 3.9 the recorded `funcname` is
# `yt_dlp.webvtt.<co_name>` (no class prefix); the line number disambiguates
# which class each `__init__` belongs to.
CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/webvtt\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.webvtt\.\S+) "
    r"event=call locals=\{.*\}$",
    re.MULTILINE,
)


# Each target is identified by (bare co_name, line number) so we can
# distinguish e.g. _MatchParser.__init__ (line 23) vs _MatchChildParser.__init__
# (line 65) vs Block.__init__ (line 122).
TARGETS = {
    "parse_ts_at_line_100": ("_parse_ts", 100),
    "commit_at_line_70": ("commit", 70),
    "block_init_at_line_122": ("__init__", 122),
    "match_at_line_27": ("match", 27),
    "matchchildparser_init_at_line_65": ("__init__", 65),
}


def extract_call_check(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No call events found in trace.")

    observed = set()
    for m in matches:
        bare = m.group("func").rsplit(".", 1)[1]
        observed.add((bare, int(m.group("lineno"))))

    return {
        key: ("yes" if pair in observed else "no")
        for key, pair in TARGETS.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/webvtt_cueblock_parse_helper_call_check/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/webvtt_cueblock_parse_helper_call_check/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_check(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/webvtt_cueblock_parse_helper_call_check_test.py`, class "
            "`TestWebvttCueblockParseHelperCallCheckQA`, method "
            "`test_webvtt_cueblock_parse_helper_call_check_case`. "
            "The test does exactly two things: "
            "(1) constructs `parser = _MatchParser(CUE_INPUT)` and "
            "(2) calls `CueBlock.parse(parser)` (defined at line 271 in "
            "`yt_dlp/webvtt.py`), with the exact `CUE_INPUT` literal at the top of the "
            "test file: `'00:00:01.500 -> 00:00:05.000\\nFirst caption\\n'`. "
            "Inside `CueBlock.parse`, the body sequence is: "
            "(a) `parser.consume(cls._REGEX_ID)` -- where `_REGEX_ID` is "
            "`r'((?:(?!-->)[^\\r\\n])+)(?:\\r\\n|[\\r\\n])'`, which captures any sequence "
            "of non-CR/LF characters NOT starting with the literal three-character "
            "`-->` sequence, terminated by a newline; "
            "(b) `m0 = parser.consume(_REGEX_TS)`; if no match, `return None`; "
            "(c) `parser.consume(cls._REGEX_ARROW)` where `_REGEX_ARROW = "
            "r'[ \\t]+-->[ \\t]+'` -- this requires the LITERAL `-->` arrow, NOT `->`; "
            "(d) `m1 = parser.consume(_REGEX_TS)`; if no match, `return None`; "
            "(e) `m2 = parser.consume(cls._REGEX_SETTINGS)`; "
            "(f) optional whitespace + NL consume; if NL fails, `return None`; "
            "(g) `start = _parse_ts(m0)`; `end = _parse_ts(m1)`; "
            "(h) build `text` by repeatedly consuming `_REGEX_PAYLOAD` until none matches; "
            "(i) `parser.commit()`; "
            "(j) `return cls(id=..., start=..., end=..., settings=..., text=...)` -- "
            "this `cls(...)` dispatches to `Block.__init__` since `CueBlock` does not "
            "define its own. Note: a CALL to `consume(r)` always invokes `match(r)` AND "
            "then `advance(...)` (the result of match), even when match returns None. "
            "Note: the `_REGEX_ID` lookahead `(?!-->)` rejects only the LITERAL three-char "
            "string `-->`; the substring `->` does NOT trigger the lookahead. "
            "Report whether each of the following yt_dlp.webvtt functions is ever called "
            "during this test (a single `event=call` for that frame anywhere in the "
            "execution counts as `yes`). On Python 3.9, the same bare name `__init__` "
            "appears for multiple classes; the line number identifies which class. "
            "Return a JSON object whose values are the lowercase string `\"yes\"` or "
            "`\"no\"` for each of these keys: "
            "`parse_ts_at_line_100` (the module-level `_parse_ts` helper, line 100), "
            "`commit_at_line_70` (`_MatchChildParser.commit`, line 70), "
            "`block_init_at_line_122` (`Block.__init__`, line 122), "
            "`match_at_line_27` (`_MatchParser.match`, line 27), "
            "`matchchildparser_init_at_line_65` (`_MatchChildParser.__init__`, line 65)."
        ),
        "template_answer": {
            "parse_ts_at_line_100": "yes_or_no",
            "commit_at_line_70": "yes_or_no",
            "block_init_at_line_122": "yes_or_no",
            "match_at_line_27": "yes_or_no",
            "matchchildparser_init_at_line_65": "yes_or_no",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
