#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_FILE_SUFFIX = "keras/src/activations/activations.py"
TRACE_LINE_RE = re.compile(
    rf"{re.escape(TARGET_FILE_SUFFIX)}:(?P<lineno>\d+)\s+"
    rf"(?P<func>\S+)\s+event=(?P<event>\w+)"
)


def _indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def locate_static_call_span(source_text: str) -> tuple[int, int]:
    lines = source_text.splitlines()
    class_line = None
    class_indent = None
    static_call_line = None
    static_call_indent = None

    for idx, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if class_line is None and re.match(r"^class\s+ReLU\b", stripped):
            class_line = idx
            class_indent = _indent_width(raw)
            continue

        if class_line is None:
            continue

        indent = _indent_width(raw)
        if (
            stripped
            and indent <= class_indent
            and not stripped.startswith("#")
            and idx > class_line
        ):
            break

        if (
            static_call_line is None
            and re.match(r"^def\s+static_call\(", stripped)
            and indent > class_indent
        ):
            static_call_line = idx
            static_call_indent = indent
            continue

        if static_call_line is not None:
            if (
                stripped
                and indent <= static_call_indent
                and not stripped.startswith("#")
            ):
                return static_call_line, idx - 1

    if static_call_line is None:
        raise ValueError("Could not locate ReLU.static_call in activations.py")

    return static_call_line, len(lines)


def extract_covered_lines(
    trace_text: str, static_call_start: int, static_call_end: int
) -> list[int]:
    covered_lines: set[int] = set()
    for match in TRACE_LINE_RE.finditer(trace_text):
        event = match.group("event")
        lineno = int(match.group("lineno"))
        if (
            event == "line"
            and static_call_start <= lineno <= static_call_end
        ):
            covered_lines.add(lineno)

    if not covered_lines:
        raise ValueError(
            "No covered lines were found in trace log for "
            "ReLU.static_call within keras/src/activations/activations.py."
        )
    return sorted(covered_lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/coverage_relu_static_call_line_branch_prediction/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/coverage_relu_static_call_line_branch_prediction/oracle.json",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/keras/src/activations/activations.py",
    )
    args = parser.parse_args()

    trace_path = Path(args.trace_log)
    trace_text = trace_path.read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    static_call_start, static_call_end = locate_static_call_span(source_text)
    covered_lines = extract_covered_lines(
        trace_text,
        static_call_start=static_call_start,
        static_call_end=static_call_end,
    )

    qa = {
        "question_kind": "M1_IntraProceduralCFG",
        "question": (
            "Use `keras/src/test/activations/relu_static_call_coverage_prediction_test.py`, "
            "class `ReLUStaticCallCoveragePredictionQATest`, and all test methods in this class. "
            "Target function: `ReLU.static_call` in `keras/src/activations/activations.py`. "
            "Exactly which line numbers of this function are covered by these tests?"
        ),
        "oracle_answer": {
            "covered_lines": covered_lines
        },
        "oracle_source": str(trace_path),
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
