#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RET_M_RE = re.compile(r"'m': '<Variable path=[^/]+/([^,]+), shape=\([^\)]*\), dtype=[^,]+, value=\[([^\]]+)\]>'")
RET_V_RE = re.compile(r"'v': '<Variable path=[^/]+/([^,]+), shape=\([^\)]*\), dtype=[^,]+, value=\[([^\]]+)\]>'")
FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def floats(s: str):
    return [float(x) for x in FLOAT_RE.findall(s)]


def eval_segment(text: str, tol=1e-12):
    observations = 0
    for line in text.splitlines():
        if "event=return" not in line or "adam.update_step" not in line:
            continue
        mm = RET_M_RE.search(line)
        vm = RET_V_RE.search(line)
        if not (mm and vm):
            continue

        m_path, m_vals = mm.group(1), floats(mm.group(2))
        v_path, v_vals = vm.group(1), floats(vm.group(2))
        observations += 1
        for j, (m, v) in enumerate(zip(m_vals, v_vals)):
            if v + tol < (m * m):
                return False, observations, {
                    "m_path": m_path,
                    "v_path": v_path,
                    "index": j,
                    "m": m,
                    "m_squared": m * m,
                    "v": v,
                }

    return True, observations, None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--trace-log", default="/testbed/logs/qa_instances/optimizers_adam_v_vs_m2_invariant/trace.log")
    p.add_argument("--out", default="/testbed/logs/qa_instances/optimizers_adam_v_vs_m2_invariant/oracle.json")
    args = p.parse_args()

    text = Path(args.trace_log).read_text(encoding="utf-8")
    segments = [s for s in text.split("[TRACE][START]") if s.strip()]

    holds = True
    total_obs = 0
    cex = None
    for seg_idx, seg in enumerate(segments):
        ok, obs, seg_cex = eval_segment(seg)
        total_obs += obs
        if not ok:
            holds = False
            cex = {"segment": seg_idx, **seg_cex}
            break

    qa = {
        "question_kind": "M7_Invariants",
        "question": (
            "Use `keras/src/test/optimizers/adam_v_vs_m2_invariant_test.py`, class "
            "`AdamVVsM2InvariantQATest`, and all 12 test methods. These tests run Adam with `amsgrad=False` "
            "and diverse multi-step gradients. In `keras/src/optimizers/adam.py`, inside `Adam.update_step`, "
            "is this invariant true within each test-method optimizer lifecycle: for every coordinate at each "
            "update, the velocity slot value `v` is always greater than or equal to `m^2` (where `m` is the "
            "momentum slot at that same update)?"
        ),
        "oracle_answer": {
            "invariant_exists": holds
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
