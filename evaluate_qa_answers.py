#!/usr/bin/env python3
"""Evaluate model answers against qa_instances oracle answers.

- Uses per-question_kind whitelists.
- Tolerant float comparison.
- Smart string comparison for paths / dotted identifiers.
- Special handling for reachability: compares only is_executed/is_called; if
  missing in oracle but oracle provides first_30_call_events, derives expected
  boolean from question + events.

Usage:
  python3 evaluate_qa_answers.py \
    --qa_root qa_instances \
    --pred_root evaluations/GPT-3.5-Codex_31_instances
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SKIP_DIRS = {"shared", "qa_artifacts"}

# Keypath whitelist per question_kind.
# Use "$" to denote the root oracle_answer (for list-valued answers).
KEYPATHS: Dict[str, List[str]] = {
    "execution_path": ["executed_path"],
    "function_call_order": ["function_call_order"],
    "call_frequency": ["call_count"],
    "dynamic_dispatch": ["concrete_class"],
    "coverage_prediction": [
        "branch_coverage.coverage_percent",
        "line_coverage.coverage_percent",
    ],
    "invariant_property": ["invariant_exists"],
    "max_stack_depth": ["max_stack_depth"],
    "variable_range": ["observed_min", "observed_max"],
    "forward_output_from_fixed_setup": ["$"],
    "tensor_shape_at_specific_location": ["$"],
    "variable_state_after_conditional_in_loop": ["$"],
    "variable_state_after_loop_before_exception_branch": ["$"],
    "variable_state_after_specific_function_call": ["$"],
    "project_raised_exception_signature": ["exception_type"],
    "exception_expectation_in_test": ["exception_type"],
    "reachability": ["is_executed", "is_called"],
}


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


def get_by_path(obj: Any, path: str) -> Tuple[bool, Any]:
    if path == "$":
        return True, obj
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def normalize_path(s: str) -> str:
    s = s.strip()
    s = s.replace("\\", "/")
    while "//" in s:
        s = s.replace("//", "/")
    if s.startswith("./"):
        s = s[2:]
    if s.endswith("/") and len(s) > 1:
        s = s[:-1]
    return s


def dotted_to_path(s: str) -> str:
    if "/" in s or "\\" in s:
        return normalize_path(s)
    if "." in s:
        return normalize_path(s.replace(".", "/"))
    return s


def normalize_identifier(s: str, key_name: str) -> List[str]:
    candidates = set()
    raw = s.strip()
    candidates.add(raw)
    candidates.add(normalize_path(raw))
    candidates.add(dotted_to_path(raw))

    if key_name and "file" in key_name:
        # For file-like strings, allow optional .py extension normalization.
        for c in list(candidates):
            if c.endswith(".py"):
                candidates.add(c[:-3])
            else:
                candidates.add(c + ".py")

    return list(candidates)


def compare_strings(a: str, b: str, key_name: str) -> bool:
    if a == b:
        return True
    a_norms = normalize_identifier(a, key_name)
    b_norms = normalize_identifier(b, key_name)
    return any(x == y for x in a_norms for y in b_norms)


def is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def compare_values(a: Any, b: Any, key_name: str, float_tol: float) -> CompareResult:
    if is_number(a) and is_number(b):
        if math.isclose(float(a), float(b), rel_tol=float_tol, abs_tol=float_tol):
            return CompareResult(True)
        return CompareResult(False, f"number_mismatch {a} != {b}")

    if isinstance(a, str) and isinstance(b, str):
        if compare_strings(a, b, key_name):
            return CompareResult(True)
        return CompareResult(False, f"string_mismatch {a} != {b}")

    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return CompareResult(False, f"list_len {len(a)} != {len(b)}")
        for i, (ai, bi) in enumerate(zip(a, b)):
            res = compare_values(ai, bi, key_name, float_tol)
            if not res.ok:
                return CompareResult(False, f"list_idx {i}: {res.reason}")
        return CompareResult(True)

    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return CompareResult(False, "dict_keys_mismatch")
        for k in a.keys():
            res = compare_values(a[k], b[k], k, float_tol)
            if not res.ok:
                return CompareResult(False, f"dict_key {k}: {res.reason}")
        return CompareResult(True)

    if a == b:
        return CompareResult(True)
    return CompareResult(False, "type_or_value_mismatch")


def extract_function_from_question(question: str) -> Optional[str]:
    # Look for a backticked identifier that looks like a fully-qualified function.
    for match in re.findall(r"`([^`]+)`", question):
        if "." in match:
            return match
    return None


def derive_reachability_expected(oracle: Dict[str, Any], question: str) -> Optional[bool]:
    events = oracle.get("first_30_call_events")
    if not isinstance(events, list):
        return None

    target = extract_function_from_question(question)
    if not target:
        return None

    for ev in events:
        if not isinstance(ev, dict):
            continue
        func = ev.get("func")
        if isinstance(func, str) and compare_strings(func, target, "func"):
            return True
    return False


def evaluate_instance(
    kind: str,
    oracle_answer: Any,
    question: str,
    pred_answer: Any,
    float_tol: float,
) -> Tuple[bool, Dict[str, bool]]:
    keypaths = KEYPATHS.get(kind)
    if not keypaths:
        raise SystemExit(f"No keypaths configured for question_kind={kind}")

    per_key_ok: Dict[str, bool] = {}

    for path in keypaths:
        if kind == "reachability" and path in {"is_executed", "is_called"}:
            ok, oracle_val = get_by_path(oracle_answer, path)
            if not ok:
                # Try derived expectation from call events.
                derived = derive_reachability_expected(oracle_answer, question)
                if derived is None:
                    per_key_ok[path] = False
                    continue
                oracle_val = derived

            ok_pred, pred_val = get_by_path(pred_answer, path)
            if not ok_pred:
                per_key_ok[path] = False
                continue
            per_key_ok[path] = compare_values(oracle_val, pred_val, path, float_tol).ok
            continue

        ok_oracle, oracle_val = get_by_path(oracle_answer, path)
        ok_pred, pred_val = get_by_path(pred_answer, path)
        if not ok_oracle or not ok_pred:
            per_key_ok[path] = False
            continue
        per_key_ok[path] = compare_values(oracle_val, pred_val, path, float_tol).ok

    instance_ok = all(per_key_ok.values()) if per_key_ok else False
    return instance_ok, per_key_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate QA answers against oracles")
    parser.add_argument("--qa_root", default="qa_instances")
    parser.add_argument("--pred_root", required=True)
    parser.add_argument("--float_tol", type=float, default=1e-6)
    args = parser.parse_args()

    qa_root = Path(args.qa_root).resolve()
    pred_root = Path(args.pred_root).resolve()

    total = 0
    correct = 0
    per_kind_total: Dict[str, int] = {}
    per_kind_correct: Dict[str, int] = {}
    per_key_total: Dict[str, int] = {}
    per_key_correct: Dict[str, int] = {}
    missing_pred = 0
    invalid_pred = 0

    for instance_dir in sorted(p for p in qa_root.iterdir() if p.is_dir()):
        if instance_dir.name in SKIP_DIRS:
            continue
        oracle_path = instance_dir / "oracle.json"
        if not oracle_path.exists():
            continue

        pred_path = pred_root / instance_dir.name / "answer.json"
        if not pred_path.exists():
            missing_pred += 1
            continue

        try:
            oracle = load_json(oracle_path)
            pred_data = load_json(pred_path)
        except Exception:
            invalid_pred += 1
            continue

        kind = oracle.get("question_kind")
        if not kind:
            continue

        oracle_answer = oracle.get("oracle_answer")
        question = oracle.get("question", "")
        pred_answer = pick_answer_payload(pred_data)

        instance_ok, per_key_ok = evaluate_instance(
            kind, oracle_answer, question, pred_answer, args.float_tol
        )

        total += 1
        per_kind_total[kind] = per_kind_total.get(kind, 0) + 1
        if instance_ok:
            correct += 1
            per_kind_correct[kind] = per_kind_correct.get(kind, 0) + 1

        for key, ok in per_key_ok.items():
            per_key_total[key] = per_key_total.get(key, 0) + 1
            if ok:
                per_key_correct[key] = per_key_correct.get(key, 0) + 1

    def pct(a: int, b: int) -> float:
        return 0.0 if b == 0 else (a / b) * 100.0

    print("Summary")
    print(f"total_instances: {total}")
    print(f"overall_accuracy: {pct(correct, total):.2f}% ({correct}/{total})")
    print(f"missing_predictions: {missing_pred}")
    print(f"invalid_predictions: {invalid_pred}")

    print("\nPer-kind accuracy")
    for kind in sorted(per_kind_total.keys()):
        k_total = per_kind_total[kind]
        k_correct = per_kind_correct.get(kind, 0)
        print(f"{kind}: {pct(k_correct, k_total):.2f}% ({k_correct}/{k_total})")

    print("\nPer-key accuracy")
    for key in sorted(per_key_total.keys()):
        k_total = per_key_total[key]
        k_correct = per_key_correct.get(key, 0)
        print(f"{key}: {pct(k_correct, k_total):.2f}% ({k_correct}/{k_total})")


if __name__ == "__main__":
    main()
