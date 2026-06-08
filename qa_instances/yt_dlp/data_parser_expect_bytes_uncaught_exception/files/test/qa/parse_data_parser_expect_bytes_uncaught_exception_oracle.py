#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# The trace plugin records each exception that escapes the
# `yt_dlp.cookies.expect_bytes` frame as an `event=exception` line of the
# form:
#   <ts> /testbed/yt_dlp/cookies.py:<line> yt_dlp.cookies.expect_bytes \
#       event=exception exc=<TypeName>: <repr(exc_val)> locals={...}
# In our test, `expect_bytes` is invoked three times: the first two succeed
# (no exception event), the third raises `ParserError` because the bytes
# read at the current cursor position do not match `expected_value`.
EXCEPTION_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/cookies\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.cookies\.expect_bytes) "
    r"event=exception exc=(?P<exc_type>[^:]+): (?P<exc_repr>.*?) locals=",
    re.MULTILINE,
)


def extract_exception(trace_text: str) -> dict:
    matches = list(EXCEPTION_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No exception event for expect_bytes in trace.")
    # The propagating exception fires once per traced frame; take the last
    # event seen for the expect_bytes frame.
    match = matches[-1]
    exc_type = match.group("exc_type").strip()
    exc_repr = match.group("exc_repr").strip()

    # `_safe_repr(exc_val)` produces e.g. `ParserError("...message...")` for
    # `repr(ParserError(...))`. Pull the inner string out via literal_eval.
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
        default="/testbed/logs/qa_instances/data_parser_expect_bytes_uncaught_exception/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/data_parser_expect_bytes_uncaught_exception/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_exception(trace_text)

    qa = {
        "question_kind": "S6_Exceptions",
        "question": (
            "Use `test/qa/data_parser_expect_bytes_uncaught_exception_test.py`, class "
            "`TestDataParserExpectBytesUncaughtExceptionQA`, method "
            "`test_data_parser_expect_bytes_uncaught_exception_case`. The test "
            "instantiates `yt_dlp.cookies.DataParser` (defined at line 584 in "
            "`yt_dlp/cookies.py`) on the literal byte buffer `b'cookies-data'`, then "
            "invokes its `expect_bytes` method three times in sequence:\n"
            "```\n"
            "p = DataParser(b'cookies-data', YDLLogger())\n"
            "p.expect_bytes(b'cook', 'magic1')\n"
            "p.expect_bytes(b'ies', 'magic2')\n"
            "with pytest.raises(Exception):\n"
            "    p.expect_bytes(b'-XYZ', 'final')\n"
            "```\n"
            "The relevant `DataParser` definitions are:\n"
            "```\n"
            "580: class ParserError(Exception):\n"
            "581:     pass\n"
            "582: \n"
            "584: class DataParser:\n"
            "585:     def __init__(self, data, logger):\n"
            "586:         self._data = data\n"
            "587:         self.cursor = 0\n"
            "588:         self._logger = logger\n"
            "589: \n"
            "590:     def read_bytes(self, num_bytes):\n"
            "591:         if num_bytes < 0:\n"
            "592:             raise ParserError(f'invalid read of {num_bytes} bytes')\n"
            "593:         end = self.cursor + num_bytes\n"
            "594:         if end > len(self._data):\n"
            "595:             raise ParserError('reached end of input')\n"
            "596:         data = self._data[self.cursor:end]\n"
            "597:         self.cursor = end\n"
            "598:         return data\n"
            "599: \n"
            "600:     def expect_bytes(self, expected_value, message):\n"
            "601:         value = self.read_bytes(len(expected_value))\n"
            "602:         if value != expected_value:\n"
            "603:             raise ParserError(f'unexpected value: {value} != {expected_value} ({message})')\n"
            "```\n\n"
            "The first two `expect_bytes` calls succeed and advance `p.cursor`. The "
            "third call (inside the `pytest.raises(Exception)` block) raises an "
            "exception that escapes the `expect_bytes` frame uncaught -- pytest catches "
            "it externally. Predict the EXACT exception that escapes the third "
            "`expect_bytes` frame:\n"
            "- `exception_type`: the bare class name (no module prefix), e.g. "
            "`ParserError`.\n"
            "- `exception_message`: the message string passed to the exception "
            "constructor, byte-for-byte (i.e. `str(exc)` of the raised exception). For "
            "an f-string like `f'unexpected value: {value} != {expected_value} "
            "({message})'`, format the bytes objects exactly as Python would interpolate "
            "them via `str.format`/`__str__` (i.e. `repr()` for `bytes`, e.g. "
            "`b'foo'`).\n\n"
            "Return a JSON object with EXACTLY these two keys:\n"
            "- `exception_type`: str -- the exception class name.\n"
            "- `exception_message`: str -- the full message, exactly."
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
