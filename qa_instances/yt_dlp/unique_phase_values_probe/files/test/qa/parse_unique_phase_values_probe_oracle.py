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


def _parse_phase_value(raw: str) -> str | None:
    raw = raw.strip()
    try:
        v = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return None
    if not isinstance(v, str):
        return None
    if v == "UNSET":
        return None
    if v.startswith("W") and len(v) == 2 and v[1].isdigit():
        return v
    return None


def extract_unique_phases(trace_text: str) -> list[str]:
    seen: set[str] = set()
    for m in LINE_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith("yt_dlp/cohort_trace.py"):
            continue
        if not m.group("func").endswith(".trace_cohort_label"):
            continue
        loc = _parse_locals_blob(m.group("locals"))
        if "phase" not in loc:
            continue
        phase = _parse_phase_value(loc["phase"])
        if phase is not None:
            seen.add(phase)
    if not seen:
        raise ValueError("No phase snapshots captured from trace log.")
    return sorted(seen)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/unique_phase_values_probe/trace.log",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/cohort_trace.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/unique_phase_values_probe/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    # Source is only used for consistency checks in other instances; keep flag for symmetry.
    _ = Path(args.source).read_text(encoding="utf-8")

    unique_values = extract_unique_phases(trace_text)

    qa = {
        "question_kind": "value_range_analysis",
        "question": (
            "Use `test/qa/unique_phase_values_probe_test.py` and execute the full parametrized test suite "
            "in that file (all cases). Inside `yt_dlp/cohort_trace.py`, function `trace_cohort_label`, "
            "consider the local variable `phase` assigned by the `if bucket == 0` / `elif bucket == 1` / "
            "`elif bucket == 2` / `elif bucket == 3` / `elif bucket == 4` / `else` chain (six string literals "
            "`W0` through `W5`). Across the entire test suite run, list every distinct string value that "
            "`phase` takes after that assignment chain completes (ignore the initial `UNSET` sentinel). "
            "Return `unique_values` as a sorted list of strings (JSON has no set type)."
        ),
        "template_answer": {
            "unique_values": ["str"],
        },
        "oracle_answer": {
            "unique_values": unique_values,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
