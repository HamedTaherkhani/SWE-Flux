#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

EXC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>[^ ]+) "
    r"event=exception exc=(?P<exc_type>[^:]+):.*? locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_caught_kinds(trace_text: str) -> dict[str, list[str]]:
    kinds: list[str] = []
    seen = set()

    for m in EXC_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith(".get_clean_interp_index"):
            continue

        exc_type = m.group("exc_type").strip()
        locals_map = ast.literal_eval(m.group("locals"))

        include = False
        if exc_type == "ValueError":
            # Original cast failure entering the exception handler.
            include = True
        elif exc_type == "TypeError" and "err" in locals_map:
            # The handler re-raises a TypeError after catching the original failure.
            include = True

        if include and exc_type not in seen:
            seen.add(exc_type)
            kinds.append(exc_type)

    if not kinds:
        raise ValueError("Could not extract benchmark exception kinds from trace.")

    return {"caught_exception_kinds": kinds}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/interp_index_caught_exception_kinds/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/interp_index_caught_exception_kinds/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_caught_kinds(trace_text)

    qa = {
        "question_kind": "C6_Exceptions",
        "question": (
            "Use `xarray/tests/qa/interp_index_caught_exception_kinds_test.py`, class "
            "`TestInterpIndexCaughtExceptionKindsHardQA`, method "
            "`test_interp_index_caught_exception_kinds_case`. "
            "The test performs two failing calls to `xarray/core/missing.py::get_clean_interp_index` "
            "that enter the `except (TypeError, ValueError)` handling path after the float64 cast "
            "attempt fails. For this benchmark, `caught_exception_kinds` means the distinct exception "
            "kinds that appear as `event=exception` inside `get_clean_interp_index` during that "
            "failing cast-and-handler sequence, including the original cast failure and the subsequent "
            "exception raised from the handler. Return them in first-seen order."
        ),
        "template_answer": {
            "caught_exception_kinds": ["str"]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
