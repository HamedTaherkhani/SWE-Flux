#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path


CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/telegram/[^:]+:\d+ [^ ]+ event=call ",
    re.MULTILINE,
)
FUNC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/telegram/[^:]+:\d+ (?P<func>[^ ]+) event=call ",
    re.MULTILINE,
)


def _round2(value: float) -> float:
    return round(float(value), 2)


def _compute_stats(values: list[int]) -> dict[str, float | int]:
    if not values:
        raise ValueError("No values to compute statistics from.")
    return {
        "avg": _round2(statistics.mean(values)),
        "median": _round2(statistics.median(values)),
        "min": min(values),
        "max": max(values),
    }


def parse_manifest(path: Path) -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        test_id, trace_path = raw.split("\t", maxsplit=1)
        rows.append((test_id, Path(trace_path)))
    if not rows:
        raise ValueError("Manifest is empty.")
    return rows


def parse_counts(trace_text: str) -> tuple[int, int]:
    total = len(CALL_RE.findall(trace_text))
    funcs = {m.group("func") for m in FUNC_RE.finditer(trace_text)}
    return total, len(funcs)


def build_oracle(manifest_rows: list[tuple[str, Path]]) -> dict:
    per_test: list[dict[str, str | int]] = []
    totals: list[int] = []
    uniques: list[int] = []

    for test_id, trace_path in manifest_rows:
        trace_text = trace_path.read_text(encoding="utf-8")
        total, unique = parse_counts(trace_text)
        per_test.append(
            {
                "test_id": test_id,
                "total_repo_function_calls": total,
                "unique_repo_functions_called": unique,
            }
        )
        totals.append(total)
        uniques.append(unique)

    return {
        "per_test": per_test,
        "summary": {
            "tests_count": len(per_test),
            "total_repo_function_calls_stats": _compute_stats(totals),
            "unique_repo_functions_called_stats": _compute_stats(uniques),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="/testbed/logs/qa_instances/suite_repo_runtime_call_counts/test_manifest.tsv",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/suite_repo_runtime_call_counts/oracle.json",
    )
    args = parser.parse_args()

    manifest_rows = parse_manifest(Path(args.manifest))
    oracle_answer = build_oracle(manifest_rows)

    qa = {
        "question_kind": "runtime_call_count_suite",
        "question": (
            "Run all tests matching `tests/qa/*_test.py` exactly as listed in the collected "
            "manifest order used by this instance. With tracing configured to "
            "`TRACE_FILE='/testbed/telegram/'`, `TRACE_EVENTS='call'`, and no function-name "
            "restriction, compute for each test: "
            "(1) `total_repo_function_calls` = number of trace events with `event=call` in "
            "`/testbed/telegram/*`, and "
            "(2) `unique_repo_functions_called` = number of distinct function names in those call "
            "events. Then compute summary statistics across tests for both metrics: "
            "`avg`, `median`, `min`, `max`."
        ),
        "template_answer": {
            "per_test": "list[{test_id: str, total_repo_function_calls: int, unique_repo_functions_called: int}]",
            "summary": {
                "tests_count": "int",
                "total_repo_function_calls_stats": "{avg: float, median: float, min: int, max: int}",
                "unique_repo_functions_called_stats": "{avg: float, median: float, min: int, max: int}",
            },
        },
        "oracle_answer": oracle_answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
