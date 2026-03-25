#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


def extract_final_focal_bce(trace_text: str) -> list[list[float]]:
    pattern = re.compile(
        r"'focal_bce': '<tf.Tensor:.*?numpy=array\((\[\[.*?\]\])(?:,\s*dtype=.*?)?\)>'",
        re.DOTALL,
    )
    matches = pattern.findall(trace_text)
    if not matches:
        raise ValueError("Could not find `focal_bce` tensor in trace log.")
    return ast.literal_eval(matches[-1].replace("\\n", "\n"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/losses_state_loop/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/losses_state_loop/oracle.json",
    )
    args = parser.parse_args()

    trace_path = Path(args.trace_log)
    trace_text = trace_path.read_text(encoding="utf-8")
    final_focal_bce = extract_final_focal_bce(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `keras/src/test/losses/losses_state_loop_test.py`, class "
            "`LossesStateLoopQATest`, method "
            "`test_running_weighted_sum_after_while_loop` (lines 8-43). "
            "In that method, a `while` loop on line 24 iterates three steps; "
            "each step calls `losses.binary_focal_crossentropy(...)` on lines "
            "26-35 with `apply_class_balancing=True`, `alpha=0.3`, "
            "`gamma=2.5`, `from_logits=True`, `axis=-1`, and "
            "`label_smoothing` chosen by the conditional on line 25 "
            "(`0.1` except step 1 uses `0.2`). For the last loop iteration "
            "(step index 2), `y_true=[[1.0, 1.0, 0.0, 0.0]]` and "
            "`y_pred=[[1.4, 0.6, -0.9, -1.6]]` (from lines 12 and 17). "
            "Inside `keras/src/losses/losses.py`, function "
            "`binary_focal_crossentropy` (starts line 2420), after "
            "`focal_bce = focal_factor * bce` (line 2483), the conditional "
            "`if apply_class_balancing:` (line 2485) updates it via "
            "`focal_bce = weight * focal_bce` (line 2487). "
            "What exact numeric value does `focal_bce` have immediately after "
            "line 2487 for that last iteration call?"
        ),
        "oracle_answer": final_focal_bce,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
