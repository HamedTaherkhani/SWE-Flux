#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)

def extract_call_frequency(trace_text: str) -> dict[str, int]:
    count = 0
    for m in CALL_RE.finditer(trace_text):
        func = m.group("func")
        if func.endswith("._iter_over_selections"):
            count += 1

    if count == 0:
        raise ValueError("Could not find target function calls in trace log.")

    return {"function_call_count": count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/groupby_selection_call_frequency/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/groupby_selection_call_frequency/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_frequency(trace_text)

    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `xarray/tests/qa/groupby_selection_call_frequency_test.py`, class "
            "`TestGroupBySelectionCallFrequencyHardQA`, method "
            "`test_groupby_selection_call_frequency_case`. "
            "The test calls `xr.apply_ufunc(...)` with a grouped input `arr.groupby('grp')` and a "
            "second argument indexed by `'grp'`. During this execution, `xarray/core/computation.py` "
            "function `_iter_over_selections` is used to iterate non-groupby arguments over group labels. "
            "How many times is `_iter_over_selections` called in this test run?"
        ),
        "template_answer": {
            "function_call_count": "int"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
