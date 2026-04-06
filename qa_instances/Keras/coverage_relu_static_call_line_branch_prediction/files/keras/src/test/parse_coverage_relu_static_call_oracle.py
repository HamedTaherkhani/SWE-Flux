#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def pct(num: int, den: int) -> float:
    if den == 0:
        return 100.0
    return round((100.0 * num) / den, 4)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--coverage-json",
        default="/testbed/logs/qa_instances/coverage_relu_static_call_line_branch_prediction/coverage.json",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/coverage_relu_static_call_line_branch_prediction/oracle.json",
    )
    args = parser.parse_args()

    obj = json.loads(Path(args.coverage_json).read_text(encoding="utf-8"))
    file_key = "keras/src/activations/activations.py"
    func_key = "ReLU.static_call"

    file_entry = obj["files"].get(file_key)
    if not file_entry:
        raise ValueError(f"Coverage JSON missing file entry: {file_key}")

    func_entry = file_entry["functions"].get(func_key)
    if not func_entry:
        available = sorted(file_entry["functions"].keys())
        raise ValueError(
            f"Coverage JSON missing function entry: {func_key}. "
            f"Available: {available}"
        )

    summary = func_entry["summary"]
    covered_lines = sorted(func_entry["executed_lines"])
    missing_lines = sorted(func_entry["missing_lines"])
    executed_branches = func_entry.get("executed_branches", [])
    missing_branches = func_entry.get("missing_branches", [])

    covered_line_count = int(summary.get("covered_lines", 0))
    num_statements = int(summary.get("num_statements", 0))
    covered_branches_count = int(summary.get("covered_branches", 0))
    num_branches = int(summary.get("num_branches", 0))

    qa = {
        "question_kind": "coverage_prediction",
        "question": (
            "Use `keras/src/test/activations/relu_static_call_coverage_prediction_test.py`, "
            "class `ReLUStaticCallCoveragePredictionQATest`, and all test methods in this class. "
            "Target function: `ReLU.static_call` in `keras/src/activations/activations.py`. "
            "Exactly which line numbers of this function are covered by these tests, and what are "
            "the exact line-coverage and branch-coverage metrics for this function?"
        ),
        "oracle_answer": {
            "covered_lines": covered_lines
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
