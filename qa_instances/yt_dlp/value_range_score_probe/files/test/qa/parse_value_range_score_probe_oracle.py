#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^(?P<path>[^:]+):(?P<lineno>\d+) (?P<func>\S+) event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _parse_locals_blob(blob: str) -> dict[str, str]:
    blob = blob.strip()
    if blob == "{}":
        return {}
    try:
        raw = ast.literal_eval(blob)
    except (ValueError, SyntaxError):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _merge_int_state(state: dict[str, int], loc: dict[str, str]) -> None:
    for k, v in loc.items():
        if k.startswith("..."):
            continue
        try:
            state[k] = int(ast.literal_eval(v))
        except (ValueError, SyntaxError, TypeError):
            continue


def _find_target_if_lineno(source_text: str) -> tuple[int, str]:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "compute_token_score":
            fn = node
            break
    if fn is None:
        raise ValueError("compute_token_score not found.")

    wanted = "score < pivot"
    for stmt in fn.body:
        if isinstance(stmt, ast.If):
            seg = ast.get_source_segment(source_text, stmt.test)
            if seg is not None and seg.strip() == wanted:
                return int(stmt.lineno), wanted
    raise ValueError("Target if `score < pivot` not found in compute_token_score.")


def extract_range(trace_text: str, *, source_text: str) -> dict[str, object]:
    if_lineno, cond = _find_target_if_lineno(source_text)
    state: dict[str, int] = {}
    seen_scores: list[int] = []

    for m in LINE_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith("yt_dlp/range_probe.py"):
            continue
        if not m.group("func").endswith(".compute_token_score"):
            continue

        lineno = int(m.group("lineno"))
        loc = _parse_locals_blob(m.group("locals"))
        _merge_int_state(state, loc)

        if lineno == if_lineno and "score" in state:
            seen_scores.append(int(state["score"]))

    if not seen_scores:
        raise ValueError("No score snapshots captured at target conditional line.")

    return {
        "target_function": "compute_token_score",
        "target_condition": cond,
        "variable_name": "score",
        "value_range": [min(seen_scores), max(seen_scores)],
        "num_observations": len(seen_scores),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/value_range_score_probe/trace.log",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/range_probe.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/value_range_score_probe/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source).read_text(encoding="utf-8")
    out = extract_range(trace_text, source_text=source_text)

    qa = {
        "question_kind": "value_range_analysis",
        "question": (
            "Use `test/qa/value_range_score_probe_test.py` and execute the full parametrized test suite "
            "in that file (all cases). Inside `yt_dlp/range_probe.py`, function `compute_token_score`, "
            "locate the `if` statement whose condition is exactly `score < pivot`. At the moment that "
            "condition is evaluated on each call during the full test suite run, the local variable "
            "`score` has a concrete integer value in [0, 255]. Considering all such evaluations across "
            "the entire suite, what is the overall inclusive range of `score` values observed? "
            "Return `value_range` as a two-element list `[min_score, max_score]`."
        ),
        "template_answer": {
            "value_range": ["int", "int"]
        },
        "oracle_answer": {
            "value_range": out["value_range"]
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

