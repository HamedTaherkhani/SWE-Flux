#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_answer(trace_text: str) -> dict[str, object]:
    # In this benchmark image, the nested helper is traced as `yt_dlp.utils._legacy._get_pixel`.
    # We count how many call-events match that exact `func` value.
    target_func = "yt_dlp.utils._legacy._get_pixel"
    count = 0
    for m in CALL_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith("yt_dlp/utils/_legacy.py"):
            continue
        if m.group("func") == target_func:
            count += 1
    return {"call_count": count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/legacy_png_pixel_call_count/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/legacy_png_pixel_call_count/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_answer(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/legacy_png_pixel_call_count_test.py`, class "
            "`TestLegacyPngPixelCallCountQA`, method "
            "`test_legacy_png_pixel_call_count_case`. In `yt_dlp/utils/_legacy.py`, "
            "function `decode_png`, there is a nested helper `def _get_pixel(idx):`. "
            "In the trace output, its `func` value appears as `yt_dlp.utils._legacy._get_pixel`. "
            "How many times is this function called during the test? Return the integer as "
            "`call_count`."
        ),
        "template_answer": {"call_count": "int"},
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
