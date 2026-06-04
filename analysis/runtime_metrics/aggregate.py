#!/usr/bin/env python3
"""Aggregate raw per-test runtime metrics into benchmark statistics.

Reads analysis/runtime_metrics/raw/<repo>.json (produced by run_repo.sh), folds
each QA instance's tests into one per-instance characterization, then reports
min / max / median (plus mean and n) for every metric, grouped by repository
and by question category (question_kind), and overall.

Per-instance folding across an instance's tests:
  - count metrics (function_calls, total_lines_executed)  -> sum
  - distinct metrics (functions, lines, files, classes)    -> size of the union
  - max_stack_depth                                         -> max

Usage:
  python aggregate.py                       # all repos under raw/
  python aggregate.py --repo Keras          # one repo
  python aggregate.py --out-json report.json --out-md report.md
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
RAW_DIR = SCRIPT_DIR / "raw"
QA_INSTANCES = PROJECT_ROOT / "qa_instances"

# Metrics reported per instance. Order matters for table output.
COUNT_METRICS = ["function_calls", "total_lines_executed", "max_stack_depth"]
DISTINCT_METRICS = ["functions", "lines", "files", "classes"]
# Friendly names for the distinct (union-size) metrics in the output.
DISTINCT_LABEL = {
    "functions": "distinct_functions",
    "lines": "lines_covered",
    "files": "files_covered",
    "classes": "classes_covered",
}
REPORT_METRICS = (
    ["function_calls"]
    + [DISTINCT_LABEL[m] for m in ("functions", "lines", "files", "classes")]
    + ["max_stack_depth", "total_lines_executed"]
)


def question_kind(repo: str, instance: str) -> str:
    oracle = QA_INSTANCES / repo / instance / "oracle.json"
    if oracle.is_file():
        try:
            return str(json.loads(oracle.read_text()).get("question_kind", "unknown"))
        except Exception:
            return "unknown"
    return "unknown"


def fold_instance(test_records: list[dict]) -> dict[str, int]:
    """Combine all tests of one instance into a single metric vector."""
    folded: dict[str, Any] = {m: 0 for m in COUNT_METRICS}
    unions: dict[str, set] = {m: set() for m in DISTINCT_METRICS}
    folded["max_stack_depth"] = 0
    for rec in test_records:
        m = rec["metrics"]
        folded["function_calls"] += m.get("function_calls", 0)
        folded["total_lines_executed"] += m.get("total_lines_executed", 0)
        folded["max_stack_depth"] = max(folded["max_stack_depth"], m.get("max_stack_depth", 0))
        for key in DISTINCT_METRICS:
            unions[key].update(m.get(key, []))
    out = {
        "function_calls": folded["function_calls"],
        "total_lines_executed": folded["total_lines_executed"],
        "max_stack_depth": folded["max_stack_depth"],
    }
    for key in DISTINCT_METRICS:
        out[DISTINCT_LABEL[key]] = len(unions[key])
    return out


def summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"n": 0, "min": 0, "max": 0, "median": 0, "mean": 0}
    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "median": round(statistics.median(values), 2),
        "mean": round(statistics.fmean(values), 2),
    }


def group_stats(instances: list[dict]) -> dict[str, dict]:
    """instances: list of {metric: value}. Return per-metric summaries."""
    return {
        metric: summarize([inst[metric] for inst in instances])
        for metric in REPORT_METRICS
    }


def load_raw(repos: list[str] | None) -> dict[str, list[dict]]:
    """Return {repo: [raw test records]}."""
    out: dict[str, list[dict]] = {}
    files = sorted(RAW_DIR.glob("*.json"))
    for f in files:
        repo = f.stem
        if repos and repo not in repos:
            continue
        data = json.loads(f.read_text())
        out[repo] = data.get("tests", [])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", action="append", help="Restrict to repo(s); repeatable.")
    ap.add_argument("--out-json", default=str(SCRIPT_DIR / "report.json"))
    ap.add_argument("--out-md", default=str(SCRIPT_DIR / "report.md"))
    args = ap.parse_args()

    raw = load_raw(args.repo)
    if not raw:
        raise SystemExit(f"No raw metric files found in {RAW_DIR}. Run run_repo.sh first.")

    # Build per-instance vectors, tagged with repo + category.
    per_instance: list[dict] = []
    for repo, records in raw.items():
        by_instance: dict[str, list[dict]] = {}
        for rec in records:
            inst = rec.get("instance") or "unknown_instance"
            by_instance.setdefault(inst, []).append(rec)
        for inst, recs in by_instance.items():
            vec = fold_instance(recs)
            vec["repo"] = repo
            vec["instance"] = inst
            vec["category"] = question_kind(repo, inst)
            vec["n_tests"] = len(recs)
            per_instance.append(vec)

    # Group by repo and by category.
    by_repo: dict[str, list[dict]] = {}
    by_cat: dict[str, list[dict]] = {}
    for vec in per_instance:
        by_repo.setdefault(vec["repo"], []).append(vec)
        by_cat.setdefault(vec["category"], []).append(vec)

    report = {
        "n_instances": len(per_instance),
        "n_repos": len(by_repo),
        "metrics": REPORT_METRICS,
        "overall": group_stats(per_instance),
        "per_repo": {repo: group_stats(v) for repo, v in sorted(by_repo.items())},
        "per_category": {cat: group_stats(v) for cat, v in sorted(by_cat.items())},
    }
    Path(args.out_json).write_text(json.dumps(report, indent=2) + "\n")

    md = render_markdown(report)
    Path(args.out_md).write_text(md)
    print(md)
    print(f"\nWrote {args.out_json} and {args.out_md}")


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append("# RepoBehave runtime metrics (per QA instance)\n")
    lines.append(
        f"Instances: {report['n_instances']} across {report['n_repos']} repo(s). "
        "Each cell is min / median / max (mean) over instances.\n"
    )

    def table(title: str, groups: dict[str, dict], key_header: str) -> None:
        lines.append(f"\n## {title}\n")
        header = "| " + key_header + " | n | " + " | ".join(report["metrics"]) + " |"
        sep = "|" + "---|" * (len(report["metrics"]) + 2)
        lines.append(header)
        lines.append(sep)
        for name, stats in groups.items():
            n = stats[report["metrics"][0]]["n"]
            cells = []
            for m in report["metrics"]:
                s = stats[m]
                cells.append(f"{s['min']}/{s['median']}/{s['max']} ({s['mean']})")
            lines.append(f"| {name} | {n} | " + " | ".join(cells) + " |")

    table("Overall", {"ALL": report["overall"]}, "scope")
    table("Per repository", report["per_repo"], "repo")
    table("Per category (question_kind)", report["per_category"], "category")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
