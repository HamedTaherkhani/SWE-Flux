#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"(?m)(?:^\d{4}-\d{2}-\d{2} .+? )?"
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call locals=(?P<locals>\{.*\})$",
)


def _is_nested_bump_call(path: str, func: str) -> bool:
    norm = path.replace("\\", "/")
    if not norm.endswith("yt_dlp/tier_mixer.py"):
        return False
    # CPython 3.11+: code.co_qualname → yt_dlp.tier_mixer.merge_ticks.<locals>.bump
    # CPython 3.9/3.10: no co_qualname on code → yt_dlp.tier_mixer.bump (co_name only)
    if func.endswith("merge_ticks.<locals>.bump"):
        return True
    return func == "yt_dlp.tier_mixer.bump"


def extract_call_count(trace_text: str) -> dict[str, object]:
    count = 0
    for m in CALL_RE.finditer(trace_text):
        if _is_nested_bump_call(m.group("path"), m.group("func")):
            count += 1
    if count == 0:
        raise ValueError("No bump call events found for yt_dlp/tier_mixer.py nested bump.")
    return {"call_count": count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/tier_mixer_call_freq/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/tier_mixer_call_freq/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_call_count(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/tier_mixer_call_freq_test.py`, class `TestTierMixerCallFreqQA`, method "
            "`test_tier_mixer_call_freq_case`. In `yt_dlp/tier_mixer.py`, function `merge_ticks`, there is a nested "
            "helper `def bump(c):` defined inside `merge_ticks`. During that single test, how many times is `bump` "
            "invoked (count only real calls, i.e. `event=call` trace rows for that nested function)? In the trace "
            "output the callee appears as `yt_dlp.tier_mixer.bump` on Python 3.9/3.10, or as "
            "`yt_dlp.tier_mixer.merge_ticks.<locals>.bump` on Python 3.11+. Count only those rows. Return the "
            "total as the integer `call_count`."
        ),
        "template_answer": {"call_count": "int"},
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
