#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

TRACE_SUFFIX = "yt_dlp/gate_resolver.py"
FUNC_SUFFIX = ".resolve_gate_span"


def _final_threshold_assign_lineno(source_text: str) -> int:
    """Line of the last `threshold = ...` before the `if x > threshold` in resolve_gate_span."""
    tree = ast.parse(source_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_gate_span":
            body = node.body
            for i, stmt in enumerate(body):
                if not isinstance(stmt, ast.If):
                    continue
                test = stmt.test
                if not (
                    isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "x"
                    and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Gt)
                    and len(test.comparators) == 1
                    and isinstance(test.comparators[0], ast.Name)
                    and test.comparators[0].id == "threshold"
                ):
                    continue
                if i == 0:
                    raise ValueError("Expected an assignment before the gate if.")
                prev = body[i - 1]
                if isinstance(prev, ast.Assign) and isinstance(prev.targets[0], ast.Name):
                    if prev.targets[0].id == "threshold":
                        return prev.lineno
                raise ValueError("Could not locate final threshold assignment before if.")
    raise ValueError("Could not locate resolve_gate_span gate if.")


def _parse_locals_blob(blob: str) -> dict[str, str]:
    blob = blob.strip()
    if blob == "{}":
        return {}
    try:
        raw = ast.literal_eval(blob)
    except (ValueError, SyntaxError):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _merge_numeric_state(state: dict[str, int], loc: dict[str, str]) -> None:
    for k, v in loc.items():
        if k.startswith("..."):
            continue
        try:
            state[k] = int(ast.literal_eval(v))
        except (ValueError, SyntaxError, TypeError):
            continue


def extract_condition_snapshot(trace_text: str, *, source_text: str) -> dict[str, object]:
    threshold_done_line = _final_threshold_assign_lineno(source_text)
    marker = " event=line locals="
    state: dict[str, int] = {}

    for raw_line in trace_text.splitlines():
        line = raw_line.strip()
        if marker not in line:
            continue
        pre, loc_blob = line.split(marker, 1)
        if "/" in pre:
            slash = pre.find("/")
            if slash > 0:
                pre = pre[slash:]
        sp = pre.rfind(" ")
        if sp == -1:
            continue
        rest, func = pre[:sp], pre[sp + 1 :]
        path_part = rest.rsplit(":", 1)[0]
        if TRACE_SUFFIX not in path_part.replace("\\", "/"):
            continue
        if not func.endswith(FUNC_SUFFIX):
            continue
        try:
            lineno = int(rest.rsplit(":", 1)[1])
        except (ValueError, IndexError):
            continue

        loc = _parse_locals_blob(loc_blob)
        # The tracer often emits `locals={}` on the `if` line (no changed locals vs the
        # prior opcode). The *final* `threshold = ...` line appears on the *previous*
        # trace row with `threshold` in changed locals. If we return as soon as
        # lineno > threshold_done_line *before* merging that row, `threshold` is still
        # the value from the *first* assignment (e.g. 13 vs 22). Snapshot at the `if`
        # by taking the first matching event with empty locals after the final threshold
        # line (AST), using state accumulated through the prior line.
        if (
            lineno > threshold_done_line
            and not loc
            and "x" in state
            and "threshold" in state
        ):
            return {
                "condition_operand_values": [state["x"], state["threshold"]],
            }

        _merge_numeric_state(state, loc)

    raise ValueError(
        "Could not capture x and threshold immediately before the first `x > threshold` evaluation."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/predicate_margin_snapshot_probe/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/predicate_margin_snapshot_probe/oracle.json",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/gate_resolver.py",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source).read_text(encoding="utf-8")
    oracle_answer = extract_condition_snapshot(trace_text, source_text=source_text)

    qa = {
        "question_kind": "conditional_statements",
        "question": (
            "Use `test/qa/predicate_margin_snapshot_probe_test.py`, class `TestPredicateMarginSnapshotProbeQA`, method "
            "`test_predicate_margin_snapshot_probe_case`. Inside `yt_dlp/gate_resolver.py`, function `resolve_gate_span`, "
            "locate the single `if` whose condition is exactly `x > threshold` (strict greater-than, local `x` on the "
            "left, local `threshold` on the right). At the first moment that condition is evaluated during this "
            "test (immediately before Python decides which branch runs), what are the exact integer values of `x` and "
            "`threshold`? Return them as `condition_operand_values`, a two-element list `[x_value, threshold_value]` "
            "in that order."
        ),
        "template_answer": {"condition_operand_values": ["int", "int"]},
        "oracle_answer": oracle_answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
