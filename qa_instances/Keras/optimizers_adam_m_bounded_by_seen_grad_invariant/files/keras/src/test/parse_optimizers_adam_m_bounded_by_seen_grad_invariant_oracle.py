#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_GRAD_RE = re.compile(r"numpy=array\(\[([^\]]+)\], dtype=float32\)")
CALL_VAR_RE = re.compile(r"'variable': \"<tf.Variable '([^']+):0'")
RET_M_RE = re.compile(r"'m': '<Variable path=[^/]+/([^,]+), shape=\([^\)]*\), dtype=[^,]+, value=\[([^\]]+)\]>'")
FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def floats(s: str):
    return [float(x) for x in FLOAT_RE.findall(s)]


def eval_segment(text: str, tol=1e-9):
    pending = []
    max_abs = {}
    observations = 0

    for line in text.splitlines():
        if "event=call" in line and "adam.update_step" in line:
            gm = CALL_GRAD_RE.search(line)
            vm = CALL_VAR_RE.search(line)
            if gm and vm:
                var = vm.group(1)
                grad = floats(gm.group(1))
                pending.append((var, grad))
        elif "event=return" in line and "adam.update_step" in line:
            mm = RET_M_RE.search(line)
            if not mm:
                continue
            m_path = mm.group(1)
            m_vals = floats(mm.group(2))
            if not pending:
                continue

            expected_var = m_path.replace("_momentum", "")
            idx = 0
            for i, (v, _g) in enumerate(pending):
                if v == expected_var:
                    idx = i
                    break
            var, grad = pending.pop(idx)

            if var not in max_abs:
                max_abs[var] = [0.0] * len(grad)
            max_abs[var] = [max(a, abs(g)) for a, g in zip(max_abs[var], grad)]

            observations += 1
            for j, m in enumerate(m_vals):
                if abs(m) > max_abs[var][j] + tol:
                    return False, observations, {
                        "variable": var,
                        "m_path": m_path,
                        "index": j,
                        "m": m,
                        "max_abs_grad_seen": max_abs[var][j],
                    }

    return True, observations, None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--trace-log", default="/testbed/logs/qa_instances/optimizers_adam_m_bounded_by_seen_grad_invariant/trace.log")
    p.add_argument("--out", default="/testbed/logs/qa_instances/optimizers_adam_m_bounded_by_seen_grad_invariant/oracle.json")
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
        "question_kind": "invariant_properties",
        "question": (
            "Use `keras/src/test/optimizers/adam_m_bounded_by_seen_grad_invariant_test.py`, class "
            "`AdamMBoundedBySeenGradInvariantQATest`, and all 12 test methods. These tests run Adam with "
            "`amsgrad=False` and diverse multi-step gradients. In `keras/src/optimizers/adam.py`, inside "
            "`Adam.update_step`, is this invariant true within each test-method optimizer lifecycle: for each "
            "coordinate of the momentum slot `m`, `abs(m)` never exceeds the maximum absolute gradient seen so "
            "far for that same variable coordinate?"
        ),
        "oracle_answer": {
            "invariant_exists": holds
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
