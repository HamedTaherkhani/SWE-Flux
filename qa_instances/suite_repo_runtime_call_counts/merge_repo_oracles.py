#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


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


def _extract_repo_entries(payload: dict) -> list[dict]:
    answer = payload.get("oracle_answer", payload)
    if isinstance(answer.get("per_repo"), list):
        return answer["per_repo"]
    raise ValueError("Input JSON does not contain 'oracle_answer.per_repo'.")


def _normalize_repo_entry(repo: dict) -> dict:
    repo_name = repo.get("repo_name", "unknown_repo")
    per_qa_instance = repo.get("per_qa_instance")

    # Backward compatibility for older shape: per_test + summary at repo level.
    if per_qa_instance is None and "per_test" in repo and "summary" in repo:
        per_qa_instance = [
            {
                "qa_instance": "unknown_instance",
                "per_test": repo["per_test"],
                "summary": repo["summary"],
            }
        ]

    if not isinstance(per_qa_instance, list) or not per_qa_instance:
        raise ValueError(f"Repo entry for {repo_name} has no per_qa_instance data.")

    repo_instance_avg_total_calls: list[float] = []
    repo_instance_avg_unique_funcs: list[float] = []
    repo_tests_total_calls: list[int] = []
    repo_tests_unique_funcs: list[int] = []
    tests_count_total = 0

    for inst in per_qa_instance:
        summary = inst["summary"]
        tests_count_total += int(summary["tests_count"])
        repo_instance_avg_total_calls.append(float(summary["total_repo_function_calls_stats"]["avg"]))
        repo_instance_avg_unique_funcs.append(float(summary["unique_repo_functions_called_stats"]["avg"]))

        for t in inst.get("per_test", []):
            repo_tests_total_calls.append(int(t["total_repo_function_calls"]))
            repo_tests_unique_funcs.append(int(t["unique_repo_functions_called"]))

    summary_over_qa_instances = {
        "qa_instances_count": len(per_qa_instance),
        "tests_count_total": tests_count_total,
        "total_repo_function_calls_per_instance_avg_stats": _compute_stats_float(repo_instance_avg_total_calls),
        "unique_repo_functions_called_per_instance_avg_stats": _compute_stats_float(repo_instance_avg_unique_funcs),
    }
    summary_over_all_tests = {
        "tests_count": tests_count_total,
        "total_repo_function_calls_stats": _compute_stats_int(repo_tests_total_calls),
        "unique_repo_functions_called_stats": _compute_stats_int(repo_tests_unique_funcs),
    }

    return {
        "repo_name": repo_name,
        "per_qa_instance": per_qa_instance,
        "summary_over_qa_instances": summary_over_qa_instances,
        "summary_over_all_tests": summary_over_all_tests,
    }


def build_merged_answer(per_repo_raw: list[dict]) -> dict:
    normalized = [_normalize_repo_entry(repo) for repo in per_repo_raw]

    all_tests_total_calls: list[int] = []
    all_tests_unique_funcs: list[int] = []
    all_instance_avg_total_calls: list[float] = []
    all_instance_avg_unique_funcs: list[float] = []
    repo_instance_counts: list[int] = []
    repo_test_counts: list[int] = []
    repo_instance_total_stats: list[dict[str, float | int]] = []
    repo_instance_unique_stats: list[dict[str, float | int]] = []

    for repo in normalized:
        s_inst = repo["summary_over_qa_instances"]
        s_tests = repo["summary_over_all_tests"]
        repo_instance_counts.append(int(s_inst["qa_instances_count"]))
        repo_test_counts.append(int(s_tests["tests_count"]))
        repo_instance_total_stats.append(s_inst["total_repo_function_calls_per_instance_avg_stats"])
        repo_instance_unique_stats.append(s_inst["unique_repo_functions_called_per_instance_avg_stats"])

        for inst in repo["per_qa_instance"]:
            all_instance_avg_total_calls.append(float(inst["summary"]["total_repo_function_calls_stats"]["avg"]))
            all_instance_avg_unique_funcs.append(float(inst["summary"]["unique_repo_functions_called_stats"]["avg"]))
            for t in inst.get("per_test", []):
                all_tests_total_calls.append(int(t["total_repo_function_calls"]))
                all_tests_unique_funcs.append(int(t["unique_repo_functions_called"]))

    return {
        "per_repo": normalized,
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
            "repos_count": len(normalized),
            "avg_qa_instances_per_repo": _round2(statistics.mean(repo_instance_counts)),
            "avg_tests_count_per_repo": _round2(statistics.mean(repo_test_counts)),
            "total_repo_function_calls_per_instance_avg_stats_avg": _compute_avg_of_stats(repo_instance_total_stats),
            "unique_repo_functions_called_per_instance_avg_stats_avg": _compute_avg_of_stats(repo_instance_unique_stats),
        },
    }


def print_summary(answer: dict) -> None:
    print("=== Per-Repo QA-Instance Summary ===")
    for repo in answer["per_repo"]:
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

    total = answer["summary_over_all_qa_instances_all_repos"]
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
    parser.add_argument("--inputs", nargs="+", required=True, help="Per-repo oracle JSON files.")
    parser.add_argument("--out", required=True, help="Path for merged oracle JSON.")
    args = parser.parse_args()

    loaded = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.inputs]
    base = loaded[0]

    merged_per_repo: list[dict] = []
    seen_repos = set()
    for payload in loaded:
        for repo in _extract_repo_entries(payload):
            repo_name = repo.get("repo_name", "unknown_repo")
            if repo_name in seen_repos:
                raise ValueError(f"Duplicate repo_name in inputs: {repo_name}")
            seen_repos.add(repo_name)
            merged_per_repo.append(repo)

    merged_answer = build_merged_answer(merged_per_repo)
    print_summary(merged_answer)

    merged_payload = {
        "question_kind": base.get("question_kind", "control_flow_prediction"),
        "question": base.get("question", ""),
        "template_answer": base.get("template_answer", {}),
        "oracle_answer": merged_answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote merged oracle: {out_path}")


if __name__ == "__main__":
    main()
