#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records the function as `yt_dlp.YoutubeDL.sanitize_info`
# (mod=yt_dlp.YoutubeDL, co_name=sanitize_info on Python 3.9).
RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/YoutubeDL\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.YoutubeDL\.sanitize_info) "
    r"event=return retval=(?P<retval>.*?) locals=\{.*\}$",
    re.MULTILINE,
)


def extract_keys(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No sanitize_info return event in trace log.")
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly 1 sanitize_info return event, got {len(matches)}.")
    retval_text = matches[0].group("retval")
    parsed = ast.literal_eval(retval_text)
    if not isinstance(parsed, dict):
        raise ValueError(f"Return value is not a dict: {parsed!r}")
    return {
        "result_keys_in_insertion_order": list(parsed.keys()),
        "result_key_count": len(parsed),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/youtubedl_sanitize_info_dict_keys/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/youtubedl_sanitize_info_dict_keys/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    keys = extract_keys(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/youtubedl_sanitize_info_dict_keys_test.py`, class "
            "`TestYoutubeDLSanitizeInfoDictKeysQA`, method "
            "`test_youtubedl_sanitize_info_dict_keys_case`. "
            "The test calls the static method `yt_dlp.YoutubeDL.YoutubeDL.sanitize_info(info_dict, "
            "remove_private_keys=True)` (defined at line 3662 in `yt_dlp/YoutubeDL.py`) with a "
            "deep copy of the exact `INFO_INPUT` dict shown at the top of the test file. "
            "The function performs three `info_dict.setdefault(...)` calls (for `epoch`, "
            "`_type`, `_version`), then -- because `remove_private_keys=True` -- builds a "
            "`reject` lambda such that any key/value pair is rejected when "
            "`v is None` OR `k.startswith('__')` OR "
            "`k in {'requested_downloads', 'requested_formats', 'requested_subtitles', "
            "'requested_entries', 'entries', 'filepath', '_filename', 'filename', "
            "'infojson_filename', 'original_url', 'playlist_autonumber'}`. "
            "It then returns `filter_fn(info_dict)` which recursively rebuilds dicts skipping "
            "rejected pairs. Note: keys starting with a *single* underscore (e.g. `_type`, "
            "`_version`, `_internal`) are NOT rejected by the `__`-prefix rule; only keys "
            "starting with two underscores are. Also note: `setdefault` on an already-present "
            "key is a no-op and does NOT change the dict's existing insertion order. "
            "Report the keys of the dict returned by `sanitize_info(...)` -- i.e. the "
            "top-level keys of the `filter_fn(info_dict)` return value. "
            "Return a JSON object with two keys: "
            "`result_keys_in_insertion_order` (list[str], the top-level keys of the returned "
            "dict in their actual insertion order, which equals the order the unrejected "
            "keys appear in `INFO_INPUT`) and "
            "`result_key_count` (int, the length of that list)."
        ),
        "template_answer": {
            "result_keys_in_insertion_order": ["str"],
            "result_key_count": "int",
        },
        "oracle_answer": keys,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
