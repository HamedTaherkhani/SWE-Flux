#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_FILE = "/testbed/telegram/ext/filters.py"
TARGET_FUNC = "telegram.ext.filters._MergedFilter.filter"
TARGET_LINE = 469

LINE_RE = re.compile(
    r"^\\d{4}-\\d{2}-\\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\\d+) "
    r"(?P<func>\\S+) event=line ",
    re.MULTILINE,
)


def extract_reachability(trace_text: str) -> dict:
    executed = False
    for match in LINE_RE.finditer(trace_text):
        path = match.group("path")
        lineno = int(match.group("lineno"))
        func = match.group("func")

        if path == TARGET_FILE and func == TARGET_FUNC and lineno == TARGET_LINE:
            executed = True
            break

    return {"block_executed": "yes" if executed else "no"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/filters_merged_or_reachability/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/filters_merged_or_reachability/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_reachability(trace_text)

    qa = {
        "question_kind": "S1_IntraProceduralCFG",
        "question": (
            "Use `tests/qa/filters_merged_or_reachability_test.py`, class "
            "`TestFiltersMergedOrReachabilityQA`, method "
            "`test_filters_merged_or_reachability_case`. "
            "This test constructs a nested filter graph and executes it via "
            "`merged_filter.check_update(update)` at line 43, traversing logic in "
            "`telegram/ext/filters.py`, `telegram/_update.py`, `telegram/_message.py`, "
            "`telegram/_chat.py`, `telegram/_user.py`, and `telegram/_messageentity.py`. "
            "In file `telegram/ext/filters.py`, function "
            "`telegram.ext.filters._MergedFilter.filter`, is the specific OR-comparison block "
            "line `469` (`comp_output = self.or_filter.check_update(update)`) ever executed "
            "during this test run? Answer with `yes` or `no`."
        ),
        "template_answer": {
            "block_executed": "yes_or_no"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
