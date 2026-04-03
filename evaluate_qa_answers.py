#!/usr/bin/env python3
"""Evaluate QA answers against oracle answers.

Usage:
  python3 evaluate_qa_answers.py --tool cursor --model gpt-5.3-codex-high --repo Sympy
  python3 evaluate_qa_answers.py --tool cursor --model gpt-5.3-codex-high --repo all
  python3 evaluate_qa_answers.py --tool llm --vendor openai --model gpt-5.4-2026-03-05 --repo Sympy
  python3 evaluate_qa_answers.py --all
"""

from __future__ import annotations

import ast
import argparse
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CompareResult:
    ok: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class EvalTarget:
    tool: str
    model: str
    repo: str
    vendor: Optional[str] = None

    def label(self) -> str:
        if self.tool.lower() == "llm" and self.vendor:
            return f"{self.tool}/{self.vendor}/{self.model}/{self.repo}"
        return f"{self.tool}/{self.model}/{self.repo}"


@dataclass
class EvalStats:
    total: int = 0
    correct: int = 0
    invalid_pred: int = 0
    missing_pred: int = 0
    missing_oracle: int = 0
    per_kind_total: Dict[str, int] = field(default_factory=dict)
    per_kind_correct: Dict[str, int] = field(default_factory=dict)
    failed_instances: List[Tuple[str, str, str]] = field(default_factory=list)  # (repo, instance, reason)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def pick_answer_payload(answer_data: Any) -> Any:
    if isinstance(answer_data, dict):
        if "oracle_answer" in answer_data:
            return answer_data["oracle_answer"]
        if "answer" in answer_data:
            return answer_data["answer"]
    return answer_data


def normalize_path(s: str) -> str:
    out = s.strip().replace("\\", "/")
    while "//" in out:
        out = out.replace("//", "/")
    if out.startswith("./"):
        out = out[2:]
    if out.endswith("/") and len(out) > 1:
        out = out[:-1]
    return out


def dotted_to_path(s: str) -> str:
    if "/" in s or "\\" in s:
        return normalize_path(s)
    if "." in s:
        return normalize_path(s.replace(".", "/"))
    return s


def normalize_identifier(s: str, key_name: str) -> List[str]:
    vals = set()
    raw = s.strip()
    vals.add(raw)
    vals.add(normalize_path(raw))
    vals.add(dotted_to_path(raw))

    if "file" in key_name.lower():
        for v in list(vals):
            if v.endswith(".py"):
                vals.add(v[:-3])
            else:
                vals.add(v + ".py")

    return list(vals)


ALT_SEPARATOR = "|||"


def _is_alt_string(s: str) -> bool:
    if ALT_SEPARATOR not in s:
        return False
    parts = [p.strip() for p in s.split(ALT_SEPARATOR)]
    return len(parts) >= 2 and all(part != "" for part in parts)


def _enum_canonical(s: str) -> str:
    token = s.strip()
    if token.startswith("<") and token.endswith(">") and len(token) > 2:
        token = token[1:-1].strip()
    if "." in token:
        token = token.split(".")[-1]
    return token.upper()


def _compare_string_single(expected: str, pred: str, key_name: str) -> bool:
    if expected == pred:
        return True

    e_norm = normalize_identifier(expected, key_name)
    p_norm = normalize_identifier(pred, key_name)
    if any(a == b for a in e_norm for b in p_norm):
        return True

    if key_name.lower() in {"type", "status"}:
        return _enum_canonical(expected) == _enum_canonical(pred)

    return False


def compare_strings(expected: str, pred: str, key_name: str) -> bool:
    if _compare_string_single(expected, pred, key_name):
        return True
    if _is_alt_string(expected):
        return any(_compare_string_single(alt.strip(), pred, key_name) for alt in expected.split(ALT_SEPARATOR))
    return False


def is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


_MAPPINGPROXY_RE = re.compile(r"^mappingproxy\((.*)\)$", re.DOTALL)


def normalize_special_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    text = value.strip()
    match = _MAPPINGPROXY_RE.fullmatch(text)
    if not match:
        return value

    inner = match.group(1).strip()
    try:
        parsed = ast.literal_eval(inner)
    except Exception:
        return value
    return parsed if isinstance(parsed, dict) else value


def compare_values(
    expected: Any,
    pred: Any,
    *,
    key_name: str,
    path: str,
    float_tol: float,
) -> CompareResult:
    expected = normalize_special_value(expected)
    pred = normalize_special_value(pred)

    if is_number(expected) and is_number(pred):
        if math.isclose(float(expected), float(pred), rel_tol=float_tol, abs_tol=float_tol):
            return CompareResult(True)
        return CompareResult(False, f"{path}: number_mismatch {expected} != {pred}")

    if isinstance(expected, str) and isinstance(pred, str):
        if compare_strings(expected, pred, key_name):
            return CompareResult(True)
        return CompareResult(False, f"{path}: string_mismatch {expected} != {pred}")

    if isinstance(expected, list):
        if not isinstance(pred, list):
            return CompareResult(False, f"{path}: type_mismatch expected=list got={type(pred).__name__}")
        if len(expected) != len(pred):
            return CompareResult(False, f"{path}: list_len {len(expected)} != {len(pred)}")
        for i, (e_item, p_item) in enumerate(zip(expected, pred)):
            child = compare_values(
                e_item,
                p_item,
                key_name=key_name,
                path=f"{path}[{i}]",
                float_tol=float_tol,
            )
            if not child.ok:
                return child
        return CompareResult(True)

    if isinstance(expected, dict):
        if not isinstance(pred, dict):
            return CompareResult(False, f"{path}: type_mismatch expected=dict got={type(pred).__name__}")
        # Flexible matching: require all expected keys, ignore extra predicted keys.
        missing = [k for k in expected.keys() if k not in pred]
        if missing:
            return CompareResult(False, f"{path}: missing_keys={missing}")
        for k, e_val in expected.items():
            child = compare_values(
                e_val,
                pred[k],
                key_name=k,
                path=f"{path}.{k}" if path != "$" else f"$.{k}",
                float_tol=float_tol,
            )
            if not child.ok:
                return child
        return CompareResult(True)

    if expected == pred:
        return CompareResult(True)
    return CompareResult(False, f"{path}: value_mismatch {expected!r} != {pred!r}")


def pct(part: int, whole: int) -> float:
    return 0.0 if whole == 0 else (part / whole) * 100.0


def has_instance_dirs(repo_root: Path) -> bool:
    if not repo_root.exists() or not repo_root.is_dir():
        return False
    for p in repo_root.iterdir():
        if not p.is_dir():
            continue
        if (p / "question.json").exists() or (p / "oracle.json").exists():
            return True
    return False


def has_prediction_dirs(pred_repo_root: Path) -> bool:
    if not pred_repo_root.exists() or not pred_repo_root.is_dir():
        return False
    for p in pred_repo_root.iterdir():
        if p.is_dir() and (p / "answer.json").exists():
            return True
    return False


def discover_repo_names(qa_root: Path) -> List[str]:
    if not qa_root.exists():
        return []
    repos = [p.name for p in qa_root.iterdir() if p.is_dir() and has_instance_dirs(p)]
    return sorted(repos)


def discover_instance_names(qa_repo_root: Path, pred_repo_root: Path) -> List[str]:
    names = set()

    if qa_repo_root.exists():
        for p in qa_repo_root.iterdir():
            if not p.is_dir():
                continue
            # qa_instances_eval instances generally contain question.json (no oracle.json).
            if (p / "question.json").exists() or (p / "oracle.json").exists():
                names.add(p.name)

    if pred_repo_root.exists():
        for p in pred_repo_root.iterdir():
            if p.is_dir() and (p / "answer.json").exists():
                names.add(p.name)

    return sorted(names)


def strict_oracle_path(repo: str, instance: str) -> Path:
    return Path("qa_instances").resolve() / repo / instance / "oracle.json"


def resolve_prediction_root(eval_root: Path, tool: str, model: str, repo: str, vendor: Optional[str]) -> Path:
    # New layout for host LLM runs: evaluations/llm/<vendor>/<model>/<repo>
    if tool.lower() == "llm":
        if vendor:
            return eval_root / "llm" / vendor.lower() / model / repo

        # Best-effort fallback: auto-detect vendor if omitted.
        llm_root = eval_root / "llm"
        if llm_root.exists():
            candidates = sorted(
                p / model / repo
                for p in llm_root.iterdir()
                if p.is_dir() and (p / model / repo).exists()
            )
            if len(candidates) == 1:
                return candidates[0]
            if len(candidates) > 1:
                matches = ", ".join(str(p.parent.name) for p in candidates)
                raise SystemExit(
                    f"Multiple vendors match model/repo under {llm_root}: {matches}. "
                    "Please pass --vendor."
                )
        raise SystemExit("For --tool llm, pass --vendor (e.g. --vendor openai).")

    # Legacy layout for existing non-LLM tools.
    return eval_root / tool / model / repo


def discover_all_targets(eval_root: Path) -> List[EvalTarget]:
    targets: List[EvalTarget] = []
    if not eval_root.exists():
        return targets

    for tool_dir in sorted(p for p in eval_root.iterdir() if p.is_dir()):
        tool = tool_dir.name
        if tool.lower() == "llm":
            for vendor_dir in sorted(p for p in tool_dir.iterdir() if p.is_dir()):
                for model_dir in sorted(p for p in vendor_dir.iterdir() if p.is_dir()):
                    for repo_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
                        if has_prediction_dirs(repo_dir):
                            targets.append(
                                EvalTarget(
                                    tool="llm",
                                    vendor=vendor_dir.name.lower(),
                                    model=model_dir.name,
                                    repo=repo_dir.name,
                                )
                            )
            continue

        for model_dir in sorted(p for p in tool_dir.iterdir() if p.is_dir()):
            for repo_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
                if has_prediction_dirs(repo_dir):
                    targets.append(
                        EvalTarget(
                            tool=tool,
                            model=model_dir.name,
                            repo=repo_dir.name,
                        )
                    )

    return targets


def merge_stats(dst: EvalStats, src: EvalStats) -> None:
    dst.total += src.total
    dst.correct += src.correct
    dst.invalid_pred += src.invalid_pred
    dst.missing_pred += src.missing_pred
    dst.missing_oracle += src.missing_oracle
    for kind, val in src.per_kind_total.items():
        dst.per_kind_total[kind] = dst.per_kind_total.get(kind, 0) + val
    for kind, val in src.per_kind_correct.items():
        dst.per_kind_correct[kind] = dst.per_kind_correct.get(kind, 0) + val
    dst.failed_instances.extend(src.failed_instances)


def evaluate_target(
    *,
    target: EvalTarget,
    qa_root: Path,
    eval_root: Path,
    float_tol: float,
    require_prediction_root: bool,
) -> EvalStats:
    qa_repo_root = qa_root / target.repo
    oracle_repo_root = Path("qa_instances").resolve() / target.repo
    pred_repo_root = resolve_prediction_root(
        eval_root=eval_root,
        tool=target.tool,
        model=target.model,
        repo=target.repo,
        vendor=target.vendor,
    )

    if not qa_repo_root.exists():
        raise SystemExit(f"QA repo directory not found: {qa_repo_root}")
    if not oracle_repo_root.exists():
        raise SystemExit(f"Oracle repo directory not found: {oracle_repo_root}")
    if require_prediction_root and not pred_repo_root.exists():
        raise SystemExit(f"Prediction repo directory not found: {pred_repo_root}")

    instance_names = discover_instance_names(qa_repo_root, pred_repo_root)

    stats = EvalStats(total=len(instance_names))
    for instance in instance_names:
        oracle_path = strict_oracle_path(target.repo, instance)
        pred_path = pred_repo_root / instance / "answer.json"

        if not oracle_path.exists():
            stats.missing_oracle += 1
            stats.failed_instances.append((target.repo, instance, "missing_oracle_json"))
            continue

        try:
            oracle = load_json(oracle_path)
        except Exception as exc:
            stats.failed_instances.append((target.repo, instance, f"invalid_oracle_json: {exc}"))
            continue

        kind = str(oracle.get("question_kind", "unknown"))
        stats.per_kind_total[kind] = stats.per_kind_total.get(kind, 0) + 1
        oracle_answer = oracle.get("oracle_answer")

        if not pred_path.exists():
            stats.missing_pred += 1
            stats.failed_instances.append((target.repo, instance, "missing_answer_json"))
            continue

        try:
            pred_raw = load_json(pred_path)
            pred_answer = pick_answer_payload(pred_raw)
        except Exception as exc:
            stats.invalid_pred += 1
            stats.failed_instances.append((target.repo, instance, f"invalid_pred_json: {exc}"))
            continue

        cmp_res = compare_values(
            expected=oracle_answer,
            pred=pred_answer,
            key_name="root",
            path="$",
            float_tol=float_tol,
        )
        if cmp_res.ok:
            stats.correct += 1
            stats.per_kind_correct[kind] = stats.per_kind_correct.get(kind, 0) + 1
        else:
            stats.failed_instances.append((target.repo, instance, cmp_res.reason or "mismatch"))

    return stats


def print_summary(scope_lines: List[str], stats: EvalStats) -> None:
    print("Summary")
    for line in scope_lines:
        print(line)
    print(f"total_instances: {stats.total}")
    print(f"overall_accuracy: {pct(stats.correct, stats.total):.2f}% ({stats.correct}/{stats.total})")
    print(f"missing_predictions: {stats.missing_pred}")
    print(f"missing_oracles: {stats.missing_oracle}")
    print(f"invalid_predictions: {stats.invalid_pred}")


def print_per_kind_accuracy(stats: EvalStats) -> None:
    print("\nPer-kind accuracy")
    if not stats.per_kind_total:
        print("none")
        return
    for kind in sorted(stats.per_kind_total.keys()):
        k_total = stats.per_kind_total[kind]
        k_correct = stats.per_kind_correct.get(kind, 0)
        print(f"{kind}: {pct(k_correct, k_total):.2f}% ({k_correct}/{k_total})")


def print_failed_instances(stats: EvalStats, single_repo: Optional[str]) -> None:
    print("\nFailed instances")
    if not stats.failed_instances:
        print("none")
        return
    for repo, instance, reason in sorted(stats.failed_instances, key=lambda x: (x[0], x[1])):
        if single_repo and repo == single_repo:
            print(f"- {instance}: {reason}")
        else:
            print(f"- {repo}/{instance}: {reason}")


def print_target_accuracies(title: str, results: List[Tuple[EvalTarget, EvalStats]], repo_only: bool = False) -> None:
    print(f"\n{title}")
    if not results:
        print("none")
        return
    for target, stats in sorted(results, key=lambda x: x[0].label()):
        label = target.repo if repo_only else target.label()
        print(f"{label}: {pct(stats.correct, stats.total):.2f}% ({stats.correct}/{stats.total})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate QA answers against oracles")
    parser.add_argument("--tool", help="Tool name under evaluations/ (e.g. cursor)")
    parser.add_argument(
        "--vendor",
        default=None,
        help="Vendor name for --tool llm (e.g. openai, gemini, anthropic)",
    )
    parser.add_argument("--model", help="Model name under evaluations/<tool>/")
    parser.add_argument("--repo", help="Repository name (e.g. Sympy) or 'all'")
    parser.add_argument("--all", action="store_true", help="Aggregate all available results across all tools/vendors/models/repos.")
    parser.add_argument("--qa-root", default="qa_instances")
    parser.add_argument("--eval-root", default="evaluations")
    parser.add_argument("--float-tol", type=float, default=1e-6)
    args = parser.parse_args()

    qa_root = Path(args.qa_root).resolve()
    eval_root = Path(args.eval_root).resolve()
    vendor = args.vendor.lower() if args.vendor else None

    if args.all and any([args.tool, args.vendor, args.model, args.repo]):
        parser.error("--all cannot be combined with --tool/--vendor/--model/--repo.")

    if args.all:
        targets = discover_all_targets(eval_root)
        if not targets:
            raise SystemExit(f"No evaluation targets found under {eval_root}")

        results: List[Tuple[EvalTarget, EvalStats]] = []
        skipped: List[Tuple[EvalTarget, str]] = []
        aggregate = EvalStats()

        for target in targets:
            try:
                stats = evaluate_target(
                    target=target,
                    qa_root=qa_root,
                    eval_root=eval_root,
                    float_tol=args.float_tol,
                    require_prediction_root=True,
                )
                results.append((target, stats))
                merge_stats(aggregate, stats)
            except SystemExit as exc:
                skipped.append((target, str(exc)))

        print_summary(
            scope_lines=[
                "scope: all",
                f"targets_evaluated: {len(results)}",
                f"targets_skipped: {len(skipped)}",
            ],
            stats=aggregate,
        )
        print_target_accuracies("Per-target accuracy", results, repo_only=False)
        print_per_kind_accuracy(aggregate)
        print_failed_instances(aggregate, single_repo=None)

        if skipped:
            print("\nSkipped targets")
            for target, reason in sorted(skipped, key=lambda x: x[0].label()):
                print(f"- {target.label()}: {reason}")
        return

    if not args.tool or not args.model or not args.repo:
        parser.error("When --all is not set, --tool, --model, and --repo are required.")

    if args.repo.lower() == "all":
        if args.tool.lower() == "llm" and not vendor:
            parser.error("For --tool llm with --repo all, pass --vendor.")

        repos = discover_repo_names(qa_root)
        if not repos:
            raise SystemExit(f"No repositories found under {qa_root}")

        results: List[Tuple[EvalTarget, EvalStats]] = []
        aggregate = EvalStats()
        for repo in repos:
            target = EvalTarget(tool=args.tool, vendor=vendor, model=args.model, repo=repo)
            stats = evaluate_target(
                target=target,
                qa_root=qa_root,
                eval_root=eval_root,
                float_tol=args.float_tol,
                require_prediction_root=False,
            )
            results.append((target, stats))
            merge_stats(aggregate, stats)

        summary_lines = [f"tool: {args.tool}"]
        if vendor:
            summary_lines.append(f"vendor: {vendor}")
        summary_lines.extend(
            [
                f"model: {args.model}",
                "repo: all",
                f"repos_evaluated: {len(results)}",
            ]
        )
        print_summary(scope_lines=summary_lines, stats=aggregate)
        print_target_accuracies("Per-repo accuracy", results, repo_only=True)
        print_per_kind_accuracy(aggregate)
        print_failed_instances(aggregate, single_repo=None)
        return

    target = EvalTarget(tool=args.tool, vendor=vendor, model=args.model, repo=args.repo)
    stats = evaluate_target(
        target=target,
        qa_root=qa_root,
        eval_root=eval_root,
        float_tol=args.float_tol,
        require_prediction_root=True,
    )

    summary_lines = [f"tool: {args.tool}"]
    if vendor:
        summary_lines.append(f"vendor: {vendor}")
    summary_lines.extend([f"model: {args.model}", f"repo: {args.repo}"])
    print_summary(scope_lines=summary_lines, stats=stats)
    print_per_kind_accuracy(stats)
    print_failed_instances(stats, single_repo=args.repo)


if __name__ == "__main__":
    main()
