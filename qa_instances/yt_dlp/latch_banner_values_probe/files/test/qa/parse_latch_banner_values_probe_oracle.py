#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"(?m)(?:^\d{4}-\d{2}-\d{2} .+? )?"
    r"(?P<path>[^:]+):(?P<lineno>\d+) (?P<func>\S+) event=line locals=(?P<locals>\{.*\})$",
)

KNOWN_STAMPS = frozenset(
    {
        "QUEUED",
        "RUNNING",
        "BLOCKED",
        "RETRY",
        "OK",
        "FAIL",
        "TIMEOUT",
        "UNKNOWN",
    }
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


def _parse_stamp(raw: str) -> str | None:
    s = raw.strip()
    if s in KNOWN_STAMPS:
        return s
    try:
        v = ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return None
    if isinstance(v, str) and v in KNOWN_STAMPS:
        return v
    return None


def extract_unique_stamps(trace_text: str) -> list[str]:
    seen: set[str] = set()
    for m in LINE_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith("yt_dlp/latch_banner.py"):
            continue
        func = m.group("func")
        if func != "yt_dlp.latch_banner.banner_lane" and not func.endswith(".banner_lane"):
            continue
        loc = _parse_locals_blob(m.group("locals"))
        if "stamp" not in loc:
            continue
        stamp = _parse_stamp(loc["stamp"])
        if stamp is not None:
            seen.add(stamp)
    if not seen:
        raise ValueError("No stamp snapshots captured from trace log.")
    return sorted(seen)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/latch_banner_values_probe/trace.log",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/latch_banner.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/latch_banner_values_probe/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    _ = Path(args.source).read_text(encoding="utf-8")
    unique_values = extract_unique_stamps(trace_text)

    qa = {
        "question_kind": "value_range_analysis",
        "question": (
            "Use `test/qa/latch_banner_values_probe_test.py`, class `TestLatchBannerValuesQA`, method "
            "`test_latch_banner_values_probe_cases`, and execute the full parametrized suite in that file "
            "(all cases; more than fifteen rows). In `yt_dlp/latch_banner.py`, function `banner_lane`, "
            "consider the local variable `stamp` assigned in the `if mix == 0` / `elif mix == 1` / "
            "`elif mix == 2` / `elif mix == 3` / `elif mix == 4` / `elif mix == 5` / `elif mix == 6` / "
            "`else` chain, where `mix` is `(int(seed) ^ len(key)) & 0x7` and the assigned literals are "
            "exactly `QUEUED`, `RUNNING`, `BLOCKED`, `RETRY`, `OK`, `FAIL`, `TIMEOUT`, and `UNKNOWN`. "
            "Across the entire suite run, list every distinct string among those eight that `stamp` takes "
            "at any traced line (ignore the initial `__unset__` placeholder). Return `unique_values` as a "
            "sorted list of strings (JSON has no set type)."
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
