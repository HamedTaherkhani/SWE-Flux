#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

CALL_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<file>/[^:]+):\d+ (?P<func>[^ ]+) event=call ",
    re.MULTILINE,
)


def _round2(value: float) -> float:
    return round(float(value), 2)


def _compute_stats_int(values: list[int]) -> dict[str, float | int]:
    if not values:
        raise ValueError("No values to compute statistics from.")
    return {
        "avg": _round2(statistics.mean(values)),
        "median": _round2(statistics.median(values)),
        "min": min(values),
        "max": max(values),
    }


def _compute_stats_float(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("No values to compute statistics from.")
    return {
        "avg": _round2(statistics.mean(values)),
        "median": _round2(statistics.median(values)),
        "min": _round2(min(values)),
        "max": _round2(max(values)),
    }


def _compute_avg_of_stats(stats_list: list[dict[str, float | int]]) -> dict[str, float]:
    if not stats_list:
        raise ValueError("No summary stats found to average.")
    keys = ("avg", "median", "min", "max")
    return {
        key: _round2(statistics.mean(float(s[key]) for s in stats_list))
        for key in keys
    }


def parse_manifest(path: Path) -> list[tuple[str, str, str, Path, str]]:
    rows: list[tuple[str, str, str, Path, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue

        parts = raw.split("\t")
        if len(parts) == 5:
            repo_name, instance_name, test_id, trace_path, trace_prefix = parts
        elif len(parts) == 4:
            repo_name, test_id, trace_path, trace_prefix = parts
            instance_name = "unknown_instance"
        elif len(parts) == 2:
            test_id, trace_path = parts
            repo_name = "Telegram_bot"
            instance_name = "unknown_instance"
            trace_prefix = "/testbed/telegram/"
        else:
            raise ValueError(f"Invalid manifest row format: {raw!r}")

        rows.append((repo_name, instance_name, test_id, Path(trace_path), trace_prefix))

    if not rows:
        raise ValueError("Manifest is empty.")
    return rows


def _exclude_prefixes(repo_name: str, trace_prefix: str) -> list[str]:
    repo = repo_name.lower()
    if "keras" in repo:
        # Keep only Keras library code and exclude test helpers/tests under keras/src/test.
        return [trace_prefix + "test/"]
    if "telegram" in repo:
        # Defensive: exclude repository-local tests if present in trace scope.
        return [trace_prefix + "tests/"]
    return []


def parse_counts(trace_text: str, trace_prefix: str, repo_name: str) -> tuple[int, int]:
    excludes = _exclude_prefixes(repo_name, trace_prefix)
    total = 0
    unique_funcs: set[tuple[str, str]] = set()

    for m in CALL_LINE_RE.finditer(trace_text):
        file_path = m.group("file")
        if not file_path.startswith(trace_prefix):
            continue
        if any(file_path.startswith(prefix) for prefix in excludes):
            continue

        func_name = m.group("func")
        total += 1
        # Distinguish same-named functions in different files.
        unique_funcs.add((file_path, func_name))

    return total, len(unique_funcs)


def build_oracle(manifest_rows: list[tuple[str, str, str, Path, str]]) -> dict:
    grouped: dict[str, dict[str, list[tuple[str, Path, str]]]] = defaultdict(lambda: defaultdict(list))
    for repo_name, instance_name, test_id, trace_path, trace_prefix in manifest_rows:
        grouped[repo_name][instance_name].append((test_id, trace_path, trace_prefix))

    per_repo: list[dict] = []
    all_tests_total_calls: list[int] = []
    all_tests_unique_funcs: list[int] = []
    all_instance_avg_total_calls: list[float] = []
    all_instance_avg_unique_funcs: list[float] = []
    repo_instance_counts: list[int] = []
    repo_test_counts: list[int] = []
    repo_instance_total_stats: list[dict[str, float | int]] = []
    repo_instance_unique_stats: list[dict[str, float | int]] = []

    for repo_name in sorted(grouped.keys()):
        per_qa_instance: list[dict] = []
        repo_instance_avg_total_calls: list[float] = []
        repo_instance_avg_unique_funcs: list[float] = []
        repo_tests_total_calls: list[int] = []
        repo_tests_unique_funcs: list[int] = []
        repo_tests_count_total = 0

        for instance_name in sorted(grouped[repo_name].keys()):
            per_test: list[dict[str, str | int]] = []
            instance_totals: list[int] = []
            instance_uniques: list[int] = []

            for test_id, trace_path, trace_prefix in grouped[repo_name][instance_name]:
                trace_text = trace_path.read_text(encoding="utf-8")
                total, unique = parse_counts(trace_text, trace_prefix, repo_name)
                per_test.append(
                    {
                        "test_id": test_id,
                        "total_repo_function_calls": total,
                        "unique_repo_functions_called": unique,
                    }
                )
                instance_totals.append(total)
                instance_uniques.append(unique)

            instance_summary = {
                "tests_count": len(per_test),
                "total_repo_function_calls_stats": _compute_stats_int(instance_totals),
                "unique_repo_functions_called_stats": _compute_stats_int(instance_uniques),
            }

            per_qa_instance.append(
                {
                    "qa_instance": instance_name,
                    "per_test": per_test,
                    "summary": instance_summary,
                }
            )

            repo_tests_count_total += len(per_test)
            repo_tests_total_calls.extend(instance_totals)
            repo_tests_unique_funcs.extend(instance_uniques)
            repo_instance_avg_total_calls.append(float(instance_summary["total_repo_function_calls_stats"]["avg"]))
            repo_instance_avg_unique_funcs.append(float(instance_summary["unique_repo_functions_called_stats"]["avg"]))

        summary_over_qa_instances = {
            "qa_instances_count": len(per_qa_instance),
            "tests_count_total": repo_tests_count_total,
            "total_repo_function_calls_per_instance_avg_stats": _compute_stats_float(repo_instance_avg_total_calls),
            "unique_repo_functions_called_per_instance_avg_stats": _compute_stats_float(repo_instance_avg_unique_funcs),
        }
        summary_over_all_tests = {
            "tests_count": repo_tests_count_total,
            "total_repo_function_calls_stats": _compute_stats_int(repo_tests_total_calls),
            "unique_repo_functions_called_stats": _compute_stats_int(repo_tests_unique_funcs),
        }

        per_repo.append(
            {
                "repo_name": repo_name,
                "per_qa_instance": per_qa_instance,
                "summary_over_qa_instances": summary_over_qa_instances,
                "summary_over_all_tests": summary_over_all_tests,
            }
        )

        all_tests_total_calls.extend(repo_tests_total_calls)
        all_tests_unique_funcs.extend(repo_tests_unique_funcs)
        all_instance_avg_total_calls.extend(repo_instance_avg_total_calls)
        all_instance_avg_unique_funcs.extend(repo_instance_avg_unique_funcs)
        repo_instance_counts.append(len(per_qa_instance))
        repo_test_counts.append(repo_tests_count_total)
        repo_instance_total_stats.append(summary_over_qa_instances["total_repo_function_calls_per_instance_avg_stats"])
        repo_instance_unique_stats.append(summary_over_qa_instances["unique_repo_functions_called_per_instance_avg_stats"])

    return {
        "per_repo": per_repo,
        "summary_over_all_qa_instances_all_repos": {
            "qa_instances_count": len(all_instance_avg_total_calls),
            "total_repo_function_calls_per_instance_avg_stats": _compute_stats_float(all_instance_avg_total_calls),
            "unique_repo_functions_called_per_instance_avg_stats": _compute_stats_float(all_instance_avg_unique_funcs),
        },
        "summary_over_all_tests_all_repos": {
            "tests_count": len(all_tests_total_calls),
            "total_repo_function_calls_stats": _compute_stats_int(all_tests_total_calls),
            "unique_repo_functions_called_stats": _compute_stats_int(all_tests_unique_funcs),
        },
        "average_summary_all_repos": {
            "repos_count": len(per_repo),
            "avg_qa_instances_per_repo": _round2(statistics.mean(repo_instance_counts)),
            "avg_tests_count_per_repo": _round2(statistics.mean(repo_test_counts)),
            "total_repo_function_calls_per_instance_avg_stats_avg": _compute_avg_of_stats(repo_instance_total_stats),
            "unique_repo_functions_called_per_instance_avg_stats_avg": _compute_avg_of_stats(repo_instance_unique_stats),
        },
    }


def print_human_summary(oracle_answer: dict) -> None:
    print("=== Per-Repo QA-Instance Summary ===")
    for repo in oracle_answer["per_repo"]:
        s = repo["summary_over_qa_instances"]
        print(
            f"- {repo['repo_name']}: qa_instances={s['qa_instances_count']}, tests={s['tests_count_total']}, "
            f"total_calls_per_instance_avg(avg/median/min/max)="
            f"{s['total_repo_function_calls_per_instance_avg_stats']['avg']}/"
            f"{s['total_repo_function_calls_per_instance_avg_stats']['median']}/"
            f"{s['total_repo_function_calls_per_instance_avg_stats']['min']}/"
            f"{s['total_repo_function_calls_per_instance_avg_stats']['max']}, "
            f"unique_funcs_per_instance_avg(avg/median/min/max)="
            f"{s['unique_repo_functions_called_per_instance_avg_stats']['avg']}/"
            f"{s['unique_repo_functions_called_per_instance_avg_stats']['median']}/"
            f"{s['unique_repo_functions_called_per_instance_avg_stats']['min']}/"
            f"{s['unique_repo_functions_called_per_instance_avg_stats']['max']}"
        )

    total = oracle_answer["summary_over_all_qa_instances_all_repos"]
    print("=== Across All Repos (QA-Instance Level) ===")
    print(
        f"qa_instances={total['qa_instances_count']}, "
        f"total_calls_per_instance_avg(avg/median/min/max)="
        f"{total['total_repo_function_calls_per_instance_avg_stats']['avg']}/"
        f"{total['total_repo_function_calls_per_instance_avg_stats']['median']}/"
        f"{total['total_repo_function_calls_per_instance_avg_stats']['min']}/"
        f"{total['total_repo_function_calls_per_instance_avg_stats']['max']}, "
        f"unique_funcs_per_instance_avg(avg/median/min/max)="
        f"{total['unique_repo_functions_called_per_instance_avg_stats']['avg']}/"
        f"{total['unique_repo_functions_called_per_instance_avg_stats']['median']}/"
        f"{total['unique_repo_functions_called_per_instance_avg_stats']['min']}/"
        f"{total['unique_repo_functions_called_per_instance_avg_stats']['max']}"
    )


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
    print_human_summary(oracle_answer)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Across benchmark QA instances, compute runtime call statistics grouped by repository and QA instance. "
            "For each QA instance, compute per-test `total_repo_function_calls` and `unique_repo_functions_called`, "
            "then summarize (`avg`, `median`, `min`, `max`) over tests in that QA instance. "
            "Count only call events whose file path is inside the current repository source prefix for that repo "
            "(excluding test files under that prefix, e.g., `keras/src/test`). "
            "Also provide summary statistics over QA instances per repository, and over all QA instances across repositories."
        ),
        "template_answer": {
            "per_repo": "list[{repo_name: str, per_qa_instance: list[{qa_instance: str, per_test: list[{test_id: str, total_repo_function_calls: int, unique_repo_functions_called: int}], summary: {tests_count: int, total_repo_function_calls_stats: {avg: float, median: float, min: int, max: int}, unique_repo_functions_called_stats: {avg: float, median: float, min: int, max: int}}}], summary_over_qa_instances: {qa_instances_count: int, tests_count_total: int, total_repo_function_calls_per_instance_avg_stats: {avg: float, median: float, min: float, max: float}, unique_repo_functions_called_per_instance_avg_stats: {avg: float, median: float, min: float, max: float}}, summary_over_all_tests: {tests_count: int, total_repo_function_calls_stats: {avg: float, median: float, min: int, max: int}, unique_repo_functions_called_stats: {avg: float, median: float, min: int, max: int}}}]",
            "summary_over_all_qa_instances_all_repos": {
                "qa_instances_count": "int",
                "total_repo_function_calls_per_instance_avg_stats": "{avg: float, median: float, min: float, max: float}",
                "unique_repo_functions_called_per_instance_avg_stats": "{avg: float, median: float, min: float, max: float}",
            },
            "summary_over_all_tests_all_repos": {
                "tests_count": "int",
                "total_repo_function_calls_stats": "{avg: float, median: float, min: int, max: int}",
                "unique_repo_functions_called_stats": "{avg: float, median: float, min: int, max: int}",
            },
            "average_summary_all_repos": {
                "repos_count": "int",
                "avg_qa_instances_per_repo": "float",
                "avg_tests_count_per_repo": "float",
                "total_repo_function_calls_per_instance_avg_stats_avg": "{avg: float, median: float, min: float, max: float}",
                "unique_repo_functions_called_per_instance_avg_stats_avg": "{avg: float, median: float, min: float, max: float}",
            },
        },
        "oracle_answer": oracle_answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
