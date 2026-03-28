#!/usr/bin/env python3
"""Evaluate QA answers against oracle answers for a specific tool/model/repo.

Usage:
  python3 evaluate_qa_answers.py --tool cursor --model gpt-5.3-codex-high --repo Sympy
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CompareResult:
    ok: bool
    reason: Optional[str] = None


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


def compare_strings(expected: str, pred: str, key_name: str) -> bool:
    if expected == pred:
        return True
    e_norm = normalize_identifier(expected, key_name)
    p_norm = normalize_identifier(pred, key_name)
    return any(a == b for a in e_norm for b in p_norm)


def is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def compare_values(
    expected: Any,
    pred: Any,
    *,
    key_name: str,
    path: str,
    float_tol: float,
) -> CompareResult:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate QA answers against oracles")
    parser.add_argument("--tool", required=True, help="Tool name under evaluations/ (e.g. cursor)")
    parser.add_argument("--model", required=True, help="Model name under evaluations/<tool>/")
    parser.add_argument("--repo", required=True, help="Repository name (e.g. Sympy)")
    parser.add_argument("--qa-root", default="qa_instances")
    parser.add_argument("--eval-root", default="evaluations")
    parser.add_argument("--float-tol", type=float, default=1e-6)
    args = parser.parse_args()

    oracle_repo_root = Path(args.qa_root).resolve() / args.repo
    pred_repo_root = Path(args.eval_root).resolve() / args.tool / args.model / args.repo

    if not oracle_repo_root.exists():
        raise SystemExit(f"Oracle repo directory not found: {oracle_repo_root}")
    if not pred_repo_root.exists():
        raise SystemExit(f"Prediction repo directory not found: {pred_repo_root}")

    instance_dirs = sorted(p for p in oracle_repo_root.iterdir() if p.is_dir())
    oracle_instances: List[Path] = [p for p in instance_dirs if (p / "oracle.json").exists()]

    total = len(oracle_instances)
    correct = 0
    invalid_pred = 0
    missing_pred = 0
    per_kind_total: Dict[str, int] = {}
    per_kind_correct: Dict[str, int] = {}
    failed_instances: List[Tuple[str, str]] = []

    for instance_dir in oracle_instances:
        instance = instance_dir.name
        oracle_path = instance_dir / "oracle.json"
        pred_path = pred_repo_root / instance / "answer.json"

        try:
            oracle = load_json(oracle_path)
        except Exception as exc:
            failed_instances.append((instance, f"invalid_oracle_json: {exc}"))
            continue

        kind = str(oracle.get("question_kind", "unknown"))
        per_kind_total[kind] = per_kind_total.get(kind, 0) + 1
        oracle_answer = oracle.get("oracle_answer")

        if not pred_path.exists():
            missing_pred += 1
            failed_instances.append((instance, "missing_answer_json"))
            continue

        try:
            pred_raw = load_json(pred_path)
            pred_answer = pick_answer_payload(pred_raw)
        except Exception as exc:
            invalid_pred += 1
            failed_instances.append((instance, f"invalid_pred_json: {exc}"))
            continue

        cmp_res = compare_values(
            expected=oracle_answer,
            pred=pred_answer,
            key_name="root",
            path="$",
            float_tol=args.float_tol,
        )
        if cmp_res.ok:
            correct += 1
            per_kind_correct[kind] = per_kind_correct.get(kind, 0) + 1
        else:
            failed_instances.append((instance, cmp_res.reason or "mismatch"))

    print("Summary")
    print(f"tool: {args.tool}")
    print(f"model: {args.model}")
    print(f"repo: {args.repo}")
    print(f"oracle_root: {oracle_repo_root}")
    print(f"prediction_root: {pred_repo_root}")
    print(f"total_instances: {total}")
    print(f"overall_accuracy: {pct(correct, total):.2f}% ({correct}/{total})")
    print(f"missing_predictions: {missing_pred}")
    print(f"invalid_predictions: {invalid_pred}")

    print("\nPer-kind accuracy")
    for kind in sorted(per_kind_total.keys()):
        k_total = per_kind_total[kind]
        k_correct = per_kind_correct.get(kind, 0)
        print(f"{kind}: {pct(k_correct, k_total):.2f}% ({k_correct}/{k_total})")

    print("\nFailed instances")
    if not failed_instances:
        print("none")
    else:
        for instance, reason in sorted(failed_instances, key=lambda x: x[0]):
            print(f"- {instance}: {reason}")


if __name__ == "__main__":
    main()
