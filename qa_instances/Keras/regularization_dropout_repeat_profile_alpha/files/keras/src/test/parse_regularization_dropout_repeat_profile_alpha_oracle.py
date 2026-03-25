#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PAYLOAD_PREFIX = "QA_PAYLOAD:"


def extract_payloads(pytest_log: str) -> list[dict]:
    payloads = []
    for line in pytest_log.splitlines():
        if line.startswith(PAYLOAD_PREFIX):
            payloads.append(json.loads(line[len(PAYLOAD_PREFIX) :]))
    if not payloads:
        raise RuntimeError("Could not find QA payload in pytest log.")
    return payloads


def output_hash(output_tensor) -> str:
    raw = json.dumps(output_tensor, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--pytest-log",
        default="/testbed/logs/qa_instances/regularization_dropout_repeat_profile_alpha/pytest.log",
    )
    p.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/regularization_dropout_repeat_profile_alpha/oracle.json",
    )
    args = p.parse_args()

    log_text = Path(args.pytest_log).read_text(encoding="utf-8")
    payloads = extract_payloads(log_text)
    payloads.sort(key=lambda x: int(x.get("run_index", 0)))

    holds = True
    counterexample = None
    if payloads:
        baseline = payloads[0].get("output_tensor")
        baseline_run = int(payloads[0].get("run_index", 1))
        baseline_hash = output_hash(baseline)
        for payload in payloads[1:]:
            observed = payload.get("output_tensor")
            observed_run = int(payload.get("run_index", baseline_run + 1))
            if observed != baseline:
                holds = False
                counterexample = {
                    "baseline_run_index": baseline_run,
                    "run_index": observed_run,
                    "baseline_output_hash": baseline_hash,
                    "observed_output_hash": output_hash(observed),
                }
                break

    qa = {
        "question_kind": "determinism_flakiness",
        "question": (
            "Use `keras/src/test/layers/regularization/dropout_repeat_profile_alpha_test.py`, class "
            "`DropoutRepeatProfileAlphaQATest`, method `test_repeated_output_profile`. This test executes "
            "one forward call and records local variable `output_tensor` (payload key `output_tensor`). "
            "For repeated executions of this same test method with identical inputs and layer configuration, "
            "does `output_tensor` remain identical across all runs?"
        ),
        "oracle_answer": {
            "invariant_exists": holds,
            "num_segments": len(payloads),
            "num_observations": max(0, len(payloads) - 1),
            "counterexample": counterexample,
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
