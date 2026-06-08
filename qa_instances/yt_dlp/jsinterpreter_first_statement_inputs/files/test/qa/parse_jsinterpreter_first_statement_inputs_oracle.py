#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# The trace plugin records the helper function's qualname as
# `<test_module>._collect_first_interpret_args`. The test module name depends on
# how pytest imports the file, so match by suffix.
RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/test/qa/jsinterpreter_first_statement_inputs_test\.py):(?P<lineno>\d+) "
    r"(?P<func>\S*\._collect_first_interpret_args) "
    r"event=return retval=(?P<retval>.*?) locals=\{.*\}$",
    re.MULTILINE,
)


def extract_snapshot(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No _collect_first_interpret_args return event in trace log.")
    if len(matches) != 1:
        raise ValueError(
            f"Expected 1 _collect_first_interpret_args return event, got {len(matches)}.")
    retval_text = matches[0].group("retval")
    parsed = ast.literal_eval(retval_text)
    if not isinstance(parsed, dict):
        raise ValueError(f"Return value is not a dict: {parsed!r}")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/jsinterpreter_first_statement_inputs/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/jsinterpreter_first_statement_inputs/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    snapshot = extract_snapshot(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `test/qa/jsinterpreter_first_statement_inputs_test.py`, class "
            "`TestJsInterpreterFirstStatementInputsQA`, method "
            "`test_jsinterpreter_first_statement_inputs_case`. "
            "The test instantiates `yt_dlp.jsinterp.JSInterpreter` (defined at line 254 in "
            "`yt_dlp/jsinterp.py`) with the exact `JS_SOURCE` string shown at the top of the "
            "test file, and then calls `jsi.call_function('compute', 4, 5, 6)`. That call "
            "indirectly invokes "
            "`yt_dlp.jsinterp.JSInterpreter.interpret_statement(self, stmt, local_vars, "
            "allow_recursion=100)` (defined at line 383). The interpreter calls "
            "`interpret_statement` many times during this evaluation; you must report the "
            "input parameter values **at the very first invocation** (the entry call made "
            "from the closure returned by `build_function`, i.e. the call at line 911). "
            "Report a JSON object with these four keys: "
            "`stmt` (str, the exact value of the `stmt` parameter at that first call -- "
            "preserve all whitespace exactly, including any runs of spaces produced by the "
            "`code.replace('\\n', ' ')` transformation in `build_function`), "
            "`local_vars_keys` (list[str], `sorted(local_vars)` -- the sorted list of all keys "
            "in the `LocalNameSpace` chain-map, including any auto-generated "
            "`__yt_dlp_jsinterp_objN` placeholder names produced by `_named_object` "
            "during `extract_function_from_code`), "
            "`argname_bindings` (object, the subset of `local_vars` keys that are NOT prefixed "
            "with `__yt_dlp_jsinterp_obj`, mapped to their values; this captures the bindings "
            "produced by `itertools.zip_longest(argnames, args, fillvalue=None)` inside "
            "`build_function.resf`), and "
            "`allow_recursion` (int, the value of the `allow_recursion` parameter at that "
            "first call -- note that `resf` passes `allow_recursion - 1` from its own default "
            "of 100). "
            "Do not include the `self` parameter; do not include placeholder-named function "
            "objects in `argname_bindings`."
        ),
        "template_answer": {
            "stmt": "str",
            "local_vars_keys": ["str"],
            "argname_bindings": {"str": "int"},
            "allow_recursion": "int",
        },
        "oracle_answer": snapshot,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
