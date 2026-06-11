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


def extract_reachability(trace_text: str) -> dict[str, bool]:
    saw_alignment_call = False
    saw_reindex_all = False

    for m in CALL_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        func = m.group("func")

        # Be robust to import locations (e.g., /testbed/xarray/... vs site-packages).
        if not path.endswith("/xarray/core/alignment.py"):
            continue

        if func.endswith(".reindex_all"):
            saw_reindex_all = True
        elif func.endswith(".align"):
            saw_alignment_call = True

    return {"target_function_called": saw_reindex_all}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/align_exact_reindexall_reachability/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/align_exact_reindexall_reachability/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_reachability(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `xarray/tests/qa/align_exact_reindexall_reachability_test.py`, class "
            "`TestAlignExactReindexAllReachabilityHardQA`, method "
            "`test_align_exact_reindexall_reachability_case`. "
            "At line 21, `xr.align(left, right, join='exact', copy=False)` is executed. "
            "Inside `xarray/core/alignment.py`, this goes through `Aligner.align`. "
            "Under this specific test run, is function `Aligner.reindex_all` ever called?"
        ),
        "template_answer": {
            "target_function_called": "bool"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
