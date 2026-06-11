#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/core/basic\.py):(?P<lineno>\d+) "
    r"(?P<func>sympy\.core\.basic\.subs) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find Basic.subs return events in trace log.")

    target = None
    for m in reversed(matches):
        parsed_locals = ast.literal_eval(m.group("locals"))
        if "redo" in parsed_locals:
            target = parsed_locals
            break

    if target is None:
        raise ValueError("Could not find local variable `redo` in Basic.subs return locals.")

    redo_raw = target["redo"]
    redo = ast.literal_eval(redo_raw)
    if not isinstance(redo, list):
        raise ValueError(f"Expected `redo` to parse into a list, got: {type(redo).__name__}")

    return {"redo": redo}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/core_subs_unordered_redo_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/core_subs_unordered_redo_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/core_subs_unordered_redo_state_test.py`, class "
            "`TestCoreSubsUnorderedRedoStateQA`, method "
            "`test_core_subs_unordered_redo_state_case`. "
            "In that test, line 18 calls `expr.subs(replacements)` where `replacements` is the dictionary created in lines 10-15. "
            "During this call, execution reaches `sympy/core/basic.py::Basic.subs` (defined at line 965). "
            "In the `if unordered:` block, line 1145 assigns "
            "`redo = [i for i, seq in enumerate(sequence) if seq[1] in _illegal]`, "
            "and line 1146 iterates over `reversed(redo)`. "
            "What exact list value does local variable `redo` hold at line 1145 for this run?"
        ),
        "template_answer": {"redo": ["int"]},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
