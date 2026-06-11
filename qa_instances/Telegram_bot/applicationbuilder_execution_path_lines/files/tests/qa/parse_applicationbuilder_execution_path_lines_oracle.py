#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for execution path extraction.")

    executed_path = []
    for match in matches:
        executed_path.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": match.group("func"),
                "line": int(match.group("lineno")),
            }
        )

    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/applicationbuilder_execution_path_lines/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/applicationbuilder_execution_path_lines/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_execution_path(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `tests/qa/applicationbuilder_execution_path_lines_test.py`, class "
            "`TestApplicationBuilderExecutionPathLinesQA`, method "
            "`test_applicationbuilder_execution_path_lines_case`. "
            "At line 8, the chained `ApplicationBuilder` call starts and reaches `.build()` at line 20. "
            "This execution traverses multiple files and classes, including "
            "`telegram/ext/_applicationbuilder.py`, `telegram/ext/_extbot.py`, "
            "`telegram/_bot.py`, `telegram/request/_httpxrequest.py`, and "
            "`telegram/ext/_application.py`. "
            "What is the exact ordered execution path as a list of objects with keys "
            "`file`, `func`, and `line`, including repeated lines?"
        ),
        "template_answer": {
            "executed_path": [
                {
                    "file": "str",
                    "func": "str",
                    "line": "int",
                }
            ]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
