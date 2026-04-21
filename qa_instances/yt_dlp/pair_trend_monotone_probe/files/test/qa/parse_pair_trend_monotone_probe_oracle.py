#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


TARGET_SUFFIX = "yt_dlp/pair_trend.py"
TARGET_FUNCS = {"yt_dlp.pair_trend.trend_read"}


def _parse_locals_blob(blob: str) -> dict[str, str]:
    blob = blob.strip()
    if blob == "{}":
        return {}
    try:
        raw = ast.literal_eval(blob)
    except (ValueError, SyntaxError):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _parse_int(raw: str) -> int | None:
    try:
        v = ast.literal_eval(raw.strip())
    except (ValueError, SyntaxError):
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return int(v)
    return None


def _locals_from_trace_row(raw_line: str) -> dict[str, str] | None:
    line = raw_line.strip()
    if " locals=" not in line:
        return None
    blob = line.rsplit(" locals=", 1)[-1].strip()
    return _parse_locals_blob(blob)


def _is_target_trend_read(path: str, func: str) -> bool:
    path = path.replace("\\", "/")
    if not path.endswith(TARGET_SUFFIX):
        return False
    if func in TARGET_FUNCS:
        return True
    return func.endswith(".trend_read")


def _parse_return_row(s: str) -> tuple[str, str, dict[str, str]] | None:
    if " event=return " not in s:
        return None
    if " locals=" not in s:
        return None
    try:
        pre, _ret = s.split(" event=return ", 1)
        last_sp = pre.rfind(" ")
        if last_sp == -1:
            return None
        func = pre[last_sp + 1 :]
        path_lineno = pre[:last_sp]
        colon = path_lineno.rfind(":")
        if colon == -1:
            return None
        path = path_lineno[:colon]
        _ = int(path_lineno[colon + 1 :])
    except ValueError:
        return None
    loc = _locals_from_trace_row(s)
    if not loc:
        return None
    return path, func, loc


def classify_monotone(pairs: list[tuple[int, int]]) -> str:
    """
    pairs: sorted list of (step, meter)

    Return one of: "increasing", "decreasing", "neither"
    - increasing: meter is non-decreasing as step increases (strict increases in step).
    - decreasing: meter is non-increasing as step increases.
    - neither: otherwise.

    If the sequence is constant, both non-decreasing and non-increasing hold; classify as "increasing".
    """
    if len(pairs) < 2:
        raise ValueError("Need at least two traced calls to classify monotonicity.")

    meters = [m for _, m in pairs]
    non_dec = all(meters[i + 1] >= meters[i] for i in range(len(meters) - 1))
    non_inc = all(meters[i + 1] <= meters[i] for i in range(len(meters) - 1))

    if non_dec:
        return "increasing"
    if non_inc:
        return "decreasing"
    return "neither"


def extract_monotone_relationship(trace_text: str) -> str:
    rows: list[tuple[int, int]] = []
    for raw in trace_text.splitlines():
        parsed = _parse_return_row(raw.strip())
        if parsed is None:
            continue
        path, func, loc = parsed
        if not _is_target_trend_read(path, func):
            continue
        if "step" not in loc or "meter" not in loc:
            continue
        step = _parse_int(loc["step"])
        meter = _parse_int(loc["meter"])
        if step is None or meter is None:
            continue
        rows.append((step, meter))

    if len(rows) < 2:
        raise ValueError("Not enough return snapshots for trend_read with step/meter locals.")

    rows.sort(key=lambda t: t[0])
    # Ensure steps are strictly increasing in the suite definition (defensive).
    for i in range(len(rows) - 1):
        if rows[i][0] >= rows[i + 1][0]:
            raise ValueError("Expected strictly increasing step order after sorting traced calls.")

    return classify_monotone(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/pair_trend_monotone_probe/trace.log",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/pair_trend.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/pair_trend_monotone_probe/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    _ = Path(args.source).read_text(encoding="utf-8")

    rel = extract_monotone_relationship(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use `test/qa/pair_trend_monotone_probe_test.py` and execute the full parametrized test suite "
            "in that file (all cases). Inside `yt_dlp/pair_trend.py`, function `trend_read`, consider "
            "the third parameter `step` and the local variable `meter` (after its final assignment before "
            "`return`). Collect one `(step, meter)` pair per call from the traced `return` locals for "
            "`trend_read`. Sort these pairs by `step` ascending. "
            "Classify the relationship of `meter` to increasing `step` across consecutive sorted pairs as "
            "`monotone_relationship`, one of exactly these strings: "
            "`increasing` if `meter` is never lower when `step` increases (i.e. non-decreasing in `step`), "
            "`decreasing` if `meter` is never higher when `step` increases (i.e. non-increasing in `step`), "
            "or `neither` if neither condition holds for all consecutive pairs. "
            "If both non-decreasing and non-increasing hold (a constant `meter` sequence), return `increasing`."
        ),
        "template_answer": {
            "monotone_relationship": "str",
        },
        "oracle_answer": {
            "monotone_relationship": rel,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
