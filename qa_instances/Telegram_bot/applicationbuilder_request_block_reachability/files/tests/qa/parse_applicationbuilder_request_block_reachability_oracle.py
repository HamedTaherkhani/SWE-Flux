#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_FILE = "/testbed/telegram/ext/_applicationbuilder.py"
TARGET_FUNC = "telegram.ext._applicationbuilder.ApplicationBuilder._build_request"
TARGET_LINE = 247

LINE_RE = re.compile(
    r"^\\d{4}-\\d{2}-\\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\\d+) "
    r"(?P<func>\\S+) event=line ",
    re.MULTILINE,
)


def extract_reachability(trace_text: str) -> dict:
    executed = False
    for match in LINE_RE.finditer(trace_text):
        if (
            match.group("path") == TARGET_FILE
            and match.group("func") == TARGET_FUNC
            and int(match.group("lineno")) == TARGET_LINE
        ):
            executed = True
            break

    return {"block_executed": "yes" if executed else "no"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/applicationbuilder_request_block_reachability/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/applicationbuilder_request_block_reachability/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_reachability(trace_text)

    qa = {
        "question_kind": "C1_IntraProceduralCFG",
        "question": (
            "Use `tests/qa/applicationbuilder_request_block_reachability_test.py`, class "
            "`TestApplicationBuilderRequestBlockReachabilityQA`, method "
            "`test_applicationbuilder_request_block_reachability_case`. "
            "The test configures an `ApplicationBuilder` with both get-updates request parameters "
            "and an explicit custom request object, then executes `builder.build()` at line 32. "
            "Execution spans `telegram/ext/_applicationbuilder.py`, "
            "`telegram/request/_httpxrequest.py`, `telegram/ext/_extbot.py`, "
            "`telegram/ext/_updater.py`, and `telegram/ext/_application.py`. "
            "In `telegram/ext/_applicationbuilder.py`, function "
            "`telegram.ext._applicationbuilder.ApplicationBuilder._build_request`, "
            "is the specific block at line `247` (`if not get_updates:`) ever executed "
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
