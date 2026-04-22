#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/lib/matplotlib/transforms.py"
TARGET_FUNC = "matplotlib.transforms.blended_transform_factory"

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/lib/matplotlib/transforms\.py):(?P<lineno>\d+) "
    r"(?P<func>matplotlib\.transforms\.blended_transform_factory) "
    r"event=return retval=(?P<retval>.+?) locals=\{"
)


def extract_retvals(trace_text: str) -> list[str]:
    retvals: list[str] = []
    for raw_line in trace_text.splitlines():
        m = RETURN_RE.match(raw_line)
        if not m:
            continue
        if m.group("path") != TARGET_PATH:
            continue
        if m.group("func") != TARGET_FUNC:
            continue
        retvals.append(m.group("retval"))
    return retvals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "blended_transform_factory_output_determinism/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "blended_transform_factory_output_determinism/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    retvals = extract_retvals(trace_text)

    invariant_exists = len(retvals) == 10 and len(set(retvals)) == 1

    qa = {
        "question_kind": "determinism_flakiness",
        "question": (
            "Execute test "
            "`tests/qa/blended_transform_factory_output_determinism_test.py::"
            "TestBlendedTransformFactoryOutputDeterminismQA::"
            "test_blended_transform_factory_output_determinism_case` "
            "exactly 10 independent times with identical inputs. In each execution, "
            "`matplotlib.transforms.blended_transform_factory` in "
            "`lib/matplotlib/transforms.py` is called once after constructing two "
            "fresh `Affine2D` pipelines built only from `.translate` and `.scale` "
            "(so each remains separable per `Affine2DBase.is_separable`): "
            "x = `Affine2D().translate(9.25, -3.5).scale(0.5, 1.25).translate(-2.1, 4.2)"
            ".scale(3.0, 3.0)` and "
            "y = `Affine2D().scale(1.125, -0.875).translate(-1.0, 6.375).translate(0.25, -0.5)"
            ".scale(0.1, 10.0)`. Is the value returned by "
            "`blended_transform_factory(x, y)` identical across all 10 executions "
            "(including object identity as observed at function return)? "
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
                "matplotlib_qa/blended_transform_factory_output_determinism/eval.sh"
            ),
            "trace_policy": {
                "trace_file_substr": "lib/matplotlib/transforms.py",
                "trace_func": "matplotlib.transforms.blended_transform_factory",
                "notes": (
                    "Return-value oracle: one return event per pytest process; "
                    "compare retval= strings across the 10 runs."
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
