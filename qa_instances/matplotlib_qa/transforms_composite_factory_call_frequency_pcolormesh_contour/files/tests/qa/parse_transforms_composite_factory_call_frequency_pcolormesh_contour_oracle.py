#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"(?P<path>(?:/testbed)?/lib/matplotlib/transforms\.py):(?P<lineno>\d+) "
    r"matplotlib\.transforms\.composite_transform_factory event=call ",
)


def extract_composite_factory_call_count(trace_text: str) -> dict:
    n = sum(1 for _ in CALL_RE.finditer(trace_text))
    if n == 0:
        raise ValueError(
            "No composite_transform_factory call events in trace; "
            "check TRACE_FILE, TRACE_FUNC, and trace format."
        )
    return {"function_call_count": n}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/transforms_composite_factory_call_frequency_pcolormesh_contour/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/transforms_composite_factory_call_frequency_pcolormesh_contour/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_composite_factory_call_count(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `tests/qa/transforms_composite_factory_call_frequency_pcolormesh_contour_test.py`, class "
            "`TestTransformsCompositeFactoryCallFrequencyPcolormeshContourQA`, method "
            "`test_transforms_composite_factory_call_frequency_pcolormesh_contour_case`. "
            "The test creates one figure with `plt.subplots()`, then calls "
            "`ax.pcolormesh(np.random.default_rng(1).random((15, 20)))`, then "
            "`ax.contour(np.random.default_rng(2).random((15, 20)), levels=5)`, then `plt.close(fig)`. "
            "Count only `event=call` trace lines in file `lib/matplotlib/transforms.py` for the qualified "
            "name `matplotlib.transforms.composite_transform_factory` (the factory used when composing "
            "transform chains, including via `+` on transforms). During the entire test run, how many "
            "times is that function called?"
        ),
        "template_answer": {
            "function_call_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
