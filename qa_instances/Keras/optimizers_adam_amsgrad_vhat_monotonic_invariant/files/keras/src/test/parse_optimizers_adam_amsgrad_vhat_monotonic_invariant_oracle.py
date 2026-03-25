#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VHAT_RE = re.compile(
    r"'v_hat': '<Variable path=([^,]+), shape=\([^\)]*\), dtype=[^,]+, value=\[([^\]]+)\]>'"
)
FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def parse_segments(trace_text: str):
    parts = trace_text.split("[TRACE][START]")
    segments = []
    for part in parts:
        if not part.strip():
            continue
        series = {}
        for path, arr in VHAT_RE.findall(part):
            vals = [float(x) for x in FLOAT_RE.findall(arr)]
            if not vals:
                continue
            series.setdefault(path, []).append(vals)
        if series:
            segments.append(series)
    if not segments:
        raise ValueError("No v_hat observations found in trace log.")
    return segments


def monotonic_non_decreasing(segments, tol=1e-9):
    for seg_idx, series in enumerate(segments):
        for path, seq in series.items():
            for i in range(1, len(seq)):
                prev = seq[i - 1]
                curr = seq[i]
                for j, (a, b) in enumerate(zip(prev, curr)):
                    if b < a - tol:
                        return False, {
                            "segment": seg_idx,
                            "path": path,
                            "step": i,
                            "index": j,
                            "prev": a,
                            "curr": b,
                        }
    return True, None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--trace-log", default="/testbed/logs/qa_instances/optimizers_adam_amsgrad_vhat_monotonic_invariant/trace.log")
    p.add_argument("--out", default="/testbed/logs/qa_instances/optimizers_adam_amsgrad_vhat_monotonic_invariant/oracle.json")
    args = p.parse_args()

    text = Path(args.trace_log).read_text(encoding="utf-8")
    segments = parse_segments(text)
    holds, counterexample = monotonic_non_decreasing(segments)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use `keras/src/test/optimizers/adam_amsgrad_vhat_monotonic_invariant_test.py`, class "
            "`AdamAmsgradVhatMonotonicInvariantQATest`, and all 12 test methods. These tests run Adam with "
            "`amsgrad=True` under diverse gradient sequences. In `keras/src/optimizers/adam.py`, inside "
            "`Adam.update_step`, is the following invariant true across the full execution trace: for each "
            "`v_hat` slot variable path, within each individual test-method run (i.e., within one optimizer "
            "lifecycle), every coordinate of `v_hat` is monotonically non-decreasing (within numerical "
            "tolerance 1e-9) over successive `update_step` calls?"
        ),
        "oracle_answer": {
            "invariant_exists": holds,
            "num_segments": len(segments),
            "num_slot_paths": sum(len(s) for s in segments),
            "num_observations": sum(len(v) for s in segments for v in s.values()),
            "counterexample": counterexample,
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
