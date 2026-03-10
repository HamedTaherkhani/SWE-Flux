#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def parse_locals(raw: str) -> dict:
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


def extract_last_float(raw: str):
    vals = FLOAT_RE.findall(raw)
    if not vals:
        return None
    return float(vals[-1])


def extract_observations(segment_text: str):
    observations = []
    for line in segment_text.splitlines():
        if "quantizers.adjust_and_nudge event=return" not in line:
            continue
        if "locals=" not in line:
            continue
        locals_dict = parse_locals(line.split("locals=", 1)[1])
        diff_raw = locals_dict.get("diff_range")
        scale_raw = locals_dict.get("scale")
        if diff_raw is None or scale_raw is None:
            continue
        diff = extract_last_float(diff_raw)
        scale = extract_last_float(scale_raw)
        if diff is None or scale is None:
            continue
        observations.append({"diff_range": diff, "scale": scale})
    return observations


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/quantizers_scale_range_dynamics/trace.log",
    )
    p.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/quantizers_scale_range_dynamics/oracle.json",
    )
    args = p.parse_args()

    text = Path(args.trace_log).read_text(encoding="utf-8")
    segments = [s for s in text.split("[TRACE][START]") if s.strip()]

    tol = 1e-12
    holds = True
    total_obs = 0
    counterexample = None

    for seg_idx, segment in enumerate(segments):
        obs = extract_observations(segment)
        for i in range(1, len(obs)):
            prev = obs[i - 1]
            curr = obs[i]
            if curr["diff_range"] <= prev["diff_range"] + tol:
                continue
            total_obs += 1
            if curr["scale"] <= prev["scale"] + tol:
                holds = False
                counterexample = {
                    "segment": seg_idx,
                    "step": i,
                    "prev_diff_range": prev["diff_range"],
                    "curr_diff_range": curr["diff_range"],
                    "prev_scale": prev["scale"],
                    "curr_scale": curr["scale"],
                }
                break
        if not holds:
            break

    qa = {
        "question_kind": "invariant_property",
        "question": (
            "Use `keras/src/test/quantizers/quantizers_scale_range_dynamics_test.py`, "
            "class `QuantizersScaleRangeDynamicsQATest`, and all 12 test methods. "
            "Each method runs a loop of calls to `keras.src.quantizers.quantizers.adjust_and_nudge` "
            "with fixed `(num_bits, narrow_range)` and progressively larger `(max_range - min_range)` "
            "values. In `keras/src/quantizers/quantizers.py`, inside `adjust_and_nudge`, does this "
            "relationship invariant hold across the full trace: whenever `diff_range` increases between "
            "successive calls within a run, computed `scale` also increases?"
        ),
        "oracle_answer": {
            "invariant_exists": holds,
            "num_segments": len(segments),
            "num_observations": total_obs,
            "counterexample": counterexample,
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
