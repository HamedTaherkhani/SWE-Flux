#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records the function as `yt_dlp.webvtt.parse_fragment` (mod=
# yt_dlp.webvtt, co_name=parse_fragment on Python 3.9). The exception that
# escapes the function frame is emitted as an `event=exception` line whose
# format is:
#   <ts> /testbed/yt_dlp/webvtt.py:<line> <funcname> event=exception exc=<Type>: <repr> locals={...}
EXCEPTION_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/webvtt\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.webvtt\.parse_fragment) "
    r"event=exception exc=(?P<exc_type>[^:]+): (?P<exc_repr>.*?) locals=",
    re.MULTILINE,
)


def extract_exception(trace_text: str) -> dict:
    matches = list(EXCEPTION_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No exception event for parse_fragment in trace.")
    # The propagating exception fires once per traced frame; take the last
    # event seen for the parse_fragment frame.
    match = matches[-1]
    exc_type = match.group("exc_type").strip()
    exc_repr = match.group("exc_repr").strip()

    # `_safe_repr(exc_val)` produces `ParseError("...message...")` for
    # `repr(ParseError(...))`. Pull the inner string out via literal_eval.
    exc_message = exc_repr
    prefix = f"{exc_type}("
    if exc_repr.startswith(prefix) and exc_repr.endswith(")"):
        inner = exc_repr[len(prefix):-1]
        try:
            exc_message = str(ast.literal_eval(inner))
        except Exception:
            exc_message = inner

    return {"exception_type": exc_type, "exception_message": exc_message}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/webvtt_parse_fragment_uncaught_exception/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/webvtt_parse_fragment_uncaught_exception/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_exception(trace_text)

    qa = {
        "question_kind": "S5_Exceptions",
        "question": (
            "Use `test/qa/webvtt_parse_fragment_uncaught_exception_test.py`, class "
            "`TestWebvttParseFragmentUncaughtExceptionQA`, method "
            "`test_webvtt_parse_fragment_uncaught_exception_case`. "
            "The test calls `list(yt_dlp.webvtt.parse_fragment(WEBVTT_BYTES))` (defined at "
            "line 356 in `yt_dlp/webvtt.py`) inside a `pytest.raises(Exception)` context, "
            "with the exact `WEBVTT_BYTES` `bytes` literal shown at the top of the test "
            "file. `parse_fragment` first decodes the bytes, then drives a `_MatchParser` "
            "through (1) `Magic.parse`, (2) a first while-loop that tries `RegionBlock`, "
            "`StyleBlock`, and `CommentBlock` in that order, breaking out as soon as none "
            "match, and (3) a second while-loop that alternates between `CommentBlock` and "
            "`CueBlock` until end-of-input, raising "
            "`yt_dlp.webvtt.ParseError(parser)` whenever none of the candidate blocks "
            "match. `ParseError.__init__` (line 79) builds its message from the *current* "
            "`parser._pos` and the next 100 characters of the data using the format "
            "`f'Parse error at position {parser._pos} (near {data!r})'`, where "
            "`data = parser._data[parser._pos : parser._pos + 100]` and `{data!r}` is "
            "Python's `repr()` of that substring. "
            "An exception escapes `parse_fragment` uncaught during this run. Report the "
            "exact exception type and exception message that propagates out of the "
            "`parse_fragment` frame -- i.e. the type's bare class name (no module prefix) "
            "and the full message string formatted by `ParseError.__init__`. "
            "Return a JSON object with two keys: `exception_type` (str, e.g. `ParseError`) "
            "and `exception_message` (str, the exact message including the position number "
            "and the `repr()`-quoted snippet, byte-for-byte)."
        ),
        "template_answer": {
            "exception_type": "str",
            "exception_message": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
