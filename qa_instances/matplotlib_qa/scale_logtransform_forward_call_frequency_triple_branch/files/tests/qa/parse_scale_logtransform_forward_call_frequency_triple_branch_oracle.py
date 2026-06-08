#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Trace lines: "<timestamp> <abs_path>:<lineno> <func> event=call ..."
CALL_RE = re.compile(
    r"(?P<path>(?:/testbed)?/lib/matplotlib/scale\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
)


def extract_forward_logtransform_call_count(trace_text: str) -> dict:
    """
    Count forward `LogTransform.transform_non_affine` only.

    The tracer reports the qualified name as `matplotlib.scale.transform_non_affine`
    for both `LogTransform` and `InvertedLogTransform`; forward log uses line 216,
    inverted uses line 252 in this tree.
    """
    n = 0
    for m in CALL_RE.finditer(trace_text):
        if m.group("lineno") != "216":
            continue
        if m.group("func") != "matplotlib.scale.transform_non_affine":
            continue
        n += 1
    if n == 0:
        raise ValueError(
            "No matching scale.py:216 transform_non_affine call events; "
            "check TRACE_FILE and trace format."
        )
    return {"function_call_count": n}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/scale_logtransform_forward_call_frequency_triple_branch/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/scale_logtransform_forward_call_frequency_triple_branch/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_forward_logtransform_call_count(trace_text)

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/scale_logtransform_forward_call_frequency_triple_branch_test.py`, class "
            "`TestScaleLogtransformForwardCallFrequencyTripleBranchQA`, method "
            "`test_scale_logtransform_forward_call_frequency_triple_branch_case`. "
            "The test does three phases in order: (1) a simple linear `plot` on default axes and `close`; "
            "(2) `plot(np.linspace(0.01, 1000, 500), np.random.default_rng(0).random(500))` with "
            "`set_xscale('log')` and `set_yscale('log')` then `close`; "
            "(3) `plot(np.linspace(-3, 3, 40), np.linspace(0.1, 10, 40))` with "
            "`set_yscale('symlog', linthresh=0.2)` then `close`. "
            "Count only `event=call` trace lines in file `lib/matplotlib/scale.py` at the line number "
            "where the **forward** `LogTransform.transform_non_affine` implementation runs "
            "(not the inverted log transform at a different line, and not symmetrical log). "
            "The trace plugin logs this method as `matplotlib.scale.transform_non_affine`; disambiguate "
            "using the line number in `scale.py` for the forward `LogTransform` body. "
            "During the entire test run, how many such calls are recorded?"
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
