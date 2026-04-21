#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _find_target_lineno(cache_source: str) -> int:
    # We target the warning emission inside Cache.load's ValueError/KeyError handler.
    needle = "self._ydl.report_warning(f'Cache retrieval from {cache_fn} failed"
    for idx, line in enumerate(cache_source.splitlines(), start=1):
        if needle in line:
            return idx
    raise ValueError("Could not locate target block line in yt_dlp/cache.py")


def extract_answer(trace_text: str, *, cache_source: str) -> dict[str, object]:
    target_lineno = _find_target_lineno(cache_source)
    for m in LINE_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith("yt_dlp/cache.py"):
            continue
        if int(m.group("lineno")) == target_lineno:
            return {"is_executed": True}
    return {"is_executed": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/cache_load_block_reachability/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/cache_load_block_reachability/oracle.json",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/cache.py",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    cache_source = Path(args.source).read_text(encoding="utf-8")

    answer = extract_answer(trace_text, cache_source=cache_source)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/cache_load_block_reachability_test.py`, class "
            "`TestCacheLoadBlockReachabilityQA`, method "
            "`test_cache_load_block_reachability_case`. In `yt_dlp/cache.py`, method "
            "`Cache.load`, consider the `except (ValueError, KeyError):` handler that computes "
            "`file_size` and then calls `self._ydl.report_warning(...)` with the message "
            "starting `Cache retrieval from`. Is the specific line that calls "
            "`self._ydl.report_warning(...)` ever executed during this test? Return "
            "`is_executed` as a boolean."
        ),
        "template_answer": {"is_executed": "bool"},
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
