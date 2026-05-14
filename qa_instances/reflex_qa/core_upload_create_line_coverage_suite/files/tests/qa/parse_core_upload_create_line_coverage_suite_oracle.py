#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dis
import json
import re
from pathlib import Path

from reflex.components.core.upload import Upload


TARGET_PATH = Path("/testbed/reflex/components/core/upload.py")
TARGET_FUNC = "reflex.components.core.upload.Upload.create"
INSTANCE_ID = "core_upload_create_line_coverage_suite"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/reflex/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
)


def executable_lines() -> list[int]:
    code = Upload.create.__func__.__code__
    return sorted({line for _, line in dis.findlinestarts(code)})


def extract_covered_lines(trace_text: str) -> list[int]:
    covered: set[int] = set()
    for raw_line in trace_text.splitlines():
        match = EVENT_RE.match(raw_line)
        if not match:
            continue
        if match.group("path") != str(TARGET_PATH):
            continue
        if match.group("func") != TARGET_FUNC:
            continue
        if match.group("event") != "line":
            continue
        covered.add(int(match.group("lineno")))
    if not covered:
        raise ValueError("No covered line events found for Upload.create.")
    return sorted(covered)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log")
    parser.add_argument("--out", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json")
    args = parser.parse_args()

    covered_lines = extract_covered_lines(Path(args.trace_log).read_text(encoding="utf-8"))
    target_lines = executable_lines()
    covered_target = set(covered_lines) & set(target_lines)
    print(
        f"coverage_rate={len(covered_target) / len(target_lines):.4f} "
        f"covered={len(covered_target)} executable={len(target_lines)}"
    )

    qa = {
        "question_kind": "M1_IntraProceduralCFG",
        "question": (
            "Run the full test suite in `tests/qa/core_upload_create_line_coverage_suite_test.py` "
            "(all 10 test classes). Focus only on `reflex/components/core/upload.py`, "
            "class method `reflex.components.core.upload.Upload.create` (lines 233-349). "
            "Count only line events whose traced function name is exactly "
            "`reflex.components.core.upload.Upload.create`; do not include called-function "
            "line events. Which exact line numbers in the target method are covered at least "
            "once by this suite? Return a JSON object with exactly one key `covered_lines`, "
            "where the value is a sorted list of unique integers in ascending order: "
            "`{\\\"covered_lines\\\": [<int>, ...]}`."
        ),
        "template_answer": {"covered_lines": []},
        "oracle_answer": {"covered_lines": covered_lines},
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
