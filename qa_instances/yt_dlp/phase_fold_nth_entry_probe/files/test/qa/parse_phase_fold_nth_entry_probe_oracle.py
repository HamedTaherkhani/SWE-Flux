#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

TRACE_SUFFIX = "yt_dlp/phase_coupler.py"
FUNC_SUFFIX = ".fold_phase_edges"
# 1-based index: each loop trip records `snap` right after `snap = acc` in the trace.
TARGET_ITERATION = 7
LOCAL_KEY = "snap"


def _parse_locals_blob(blob: str) -> dict[str, str]:
    blob = blob.strip()
    if blob == "{}":
        return {}
    try:
        raw = ast.literal_eval(blob)
    except (ValueError, SyntaxError):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def extract_nth_iteration_snap(trace_text: str) -> dict[str, object]:
    """Use trace events where `snap` appears in changed locals (post `snap = acc`).

    Line numbers for `snap = acc` can differ across hosts (blank lines / tooling); matching
    on `snap` plus `fold_phase_edges` is stable across environments.
    """
    marker = " event=line locals="
    hits: list[int] = []

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
        if TRACE_SUFFIX not in rest.replace("\\", "/"):
            continue
        if not func.endswith(FUNC_SUFFIX):
            continue
        loc = _parse_locals_blob(loc_blob)
        if LOCAL_KEY not in loc:
            continue
        try:
            hits.append(int(ast.literal_eval(loc[LOCAL_KEY])))
        except (ValueError, SyntaxError):
            hits.append(int(loc[LOCAL_KEY]))

    if len(hits) < TARGET_ITERATION:
        raise ValueError(
            f"Expected at least {TARGET_ITERATION} `{LOCAL_KEY}` updates in {FUNC_SUFFIX} "
            f"for {TRACE_SUFFIX}, got {len(hits)}."
        )
    value = hits[TARGET_ITERATION - 1]
    return {"acc_at_iteration_start": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/phase_fold_nth_entry_probe/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/phase_fold_nth_entry_probe/oracle.json",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/phase_coupler.py",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    oracle_answer = extract_nth_iteration_snap(trace_text)

    qa = {
        "question_kind": "iterations",
        "question": (
            "Use `test/qa/phase_fold_nth_entry_probe_test.py`, class `TestPhaseFoldNthEntryProbeQA`, method "
            "`test_phase_fold_nth_entry_probe_case`. Inside `yt_dlp/phase_coupler.py`, function `fold_phase_edges`, "
            "consider the single `while` loop with header `while cursor < bound:`. Number loop-body entries so the "
            "first time control runs a statement inside that loop is iteration 1, the next full entry is iteration 2, "
            "and so on. On iteration 7, the first statement in the loop body is `snap = acc`, which copies the "
            "current `acc` into `snap` before `acc` is updated for that iteration. What is the exact integer value of "
            "`acc` at that moment (equivalently the new value of `snap` immediately after that assignment runs)? Return "
            "it as the integer `acc_at_iteration_start`."
        ),
        "template_answer": {"acc_at_iteration_start": "int"},
        "oracle_answer": oracle_answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
