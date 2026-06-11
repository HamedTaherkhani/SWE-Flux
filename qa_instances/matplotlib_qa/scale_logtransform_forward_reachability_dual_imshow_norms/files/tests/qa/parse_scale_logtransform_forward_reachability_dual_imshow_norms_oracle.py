#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Forward `LogTransform.transform_non_affine` — tracer uses `matplotlib.scale.transform_non_affine`;
# inverted log uses a different line in `scale.py`.
FORWARD_LOG_TRANSFORM_RE = re.compile(
    r"(?P<path>(?:/testbed)?/lib/matplotlib/scale\.py):216 "
    r"matplotlib\.scale\.transform_non_affine event=call ",
)


def extract_reachable(trace_text: str) -> dict:
    n = sum(1 for _ in FORWARD_LOG_TRANSFORM_RE.finditer(trace_text))
    return {"reachable": n > 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/scale_logtransform_forward_reachability_dual_imshow_norms/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/scale_logtransform_forward_reachability_dual_imshow_norms/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_reachable(trace_text)

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "subcategory": "reachability",
        "question": (
            "Use `tests/qa/scale_logtransform_forward_reachability_dual_imshow_norms_test.py`, class "
            "`TestScaleLogtransformForwardReachabilityDualImshowNormsQA`, method "
            "`test_scale_logtransform_forward_reachability_dual_imshow_norms_case`. "
            "The test builds `z = np.random.default_rng(7).random((10, 12)) * 50 + 0.05`, then "
            "`fig, axes = plt.subplots(1, 2)`, then `axes[0].imshow(z, norm=matplotlib.colors.Normalize())` "
            "and `axes[1].imshow(z, norm=matplotlib.colors.LogNorm())`, then `plt.close(fig)`. "
            "Consider execution over the **entire** test. Does control **ever** reach the **forward** "
            "`LogTransform.transform_non_affine` implementation in `lib/matplotlib/scale.py` (the body that "
            "applies the logarithm in data space)? The trace plugin logs this method as "
            "`matplotlib.scale.transform_non_affine`; disambiguate from the inverted-log implementation on "
            "another line by using line **216** in `scale.py` in this source tree. Answer whether that site is "
            "**reachable** at least once (true) or never (false)."
        ),
        "template_answer": {
            "reachable": "bool",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
