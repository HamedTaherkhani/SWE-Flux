#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/lib/matplotlib/transforms.py"
TARGET_FUNC = "matplotlib.transforms.composite_transform_factory"

START_RE = re.compile(r"\[TRACE\]\[START\]")
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/lib/matplotlib/transforms\.py):(?P<lineno>\d+) "
    r"(?P<func>matplotlib\.transforms\.composite_transform_factory) "
    r"event=(?P<event>call|line|return|exception)\b"
)


def extract_sequences(trace_text: str) -> list[list[int]]:
    sequences: list[list[int]] = []
    current: list[int] = []
    started = False

    for raw_line in trace_text.splitlines():
        if START_RE.search(raw_line):
            if started:
                sequences.append(current)
                current = []
            else:
                started = True
            continue

        if not started:
            continue

        m = LINE_RE.match(raw_line)
        if not m:
            continue
        if m.group("path") != TARGET_PATH:
            continue
        if m.group("func") != TARGET_FUNC:
            continue
        if m.group("event") != "line":
            continue
        current.append(int(m.group("lineno")))

    if started:
        sequences.append(current)

    return sequences


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "composite_transform_factory_line_path_determinism/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "composite_transform_factory_line_path_determinism/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    sequences = extract_sequences(trace_text)

    invariant_exists = (
        len(sequences) == 10
        and all(seq for seq in sequences)
        and all(seq == sequences[0] for seq in sequences[1:])
    )

    qa = {
        "question_kind": "C1_IntraProceduralCFG",
        "question": (
            "Execute test "
            "`tests/qa/composite_transform_factory_line_path_determinism_test.py::"
            "TestCompositeTransformFactoryLinePathDeterminismQA::"
            "test_composite_transform_factory_line_path_determinism_case` "
            "exactly 10 independent times with identical inputs. In each execution, focus on "
            "`lib/matplotlib/transforms.py`, function "
            "`matplotlib.transforms.composite_transform_factory`. "
            "The test calls the factory once with a = "
            "`Affine2D().rotate_deg(-12.0).scale(0.5, 2.0).translate(1.0, -2.0)` and b = "
            "`Affine2D().skew_deg(5.0, -3.0).rotate_deg(40.0).translate(0.25, 0.25)` "
            "(both `Affine2D`, neither `IdentityTransform`). "
            "Do repeated runs follow the exact same sequence of executed line numbers "
            "inside this target function? "
            "Return JSON with exactly one key: `{\"invariant_exists\": <bool>}`."
        ),
        "template_answer": {
            "invariant_exists": "bool",
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists,
        },
        "execution": {
            "eval_entry": (
                "matplotlib_qa/composite_transform_factory_line_path_determinism/eval.sh"
            ),
            "trace_policy": {
                "trace_file_substr": "lib/matplotlib/transforms.py",
                "trace_func": "matplotlib.transforms.composite_transform_factory",
                "notes": (
                    "Line-path oracle: TRACE_LOG_ALL_LINES=1; compare lineno sequences "
                    "between [TRACE][START] markers for 10 pytest invocations."
                ),
            },
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
