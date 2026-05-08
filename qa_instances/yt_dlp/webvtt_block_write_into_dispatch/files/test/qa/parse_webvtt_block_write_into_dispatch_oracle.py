#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# Trace plugin records every `event=call` for any frame inside
# /testbed/yt_dlp/webvtt.py. On Python 3.9 the recorded `funcname` drops the
# class prefix, but the line number where the function is DEFINED uniquely
# identifies which class's body each `write_into` belongs to.
CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/webvtt\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.webvtt\.\S+) "
    r"event=call locals=\{.*\}$",
    re.MULTILINE,
)


# Each `write_into` is defined once per class; the def-line is unique.
WRITE_INTO_DEF_LINE_TO_CLASS = {
    134: "Block",
    221: "Magic",
    311: "CueBlock",
}


def extract_dispatch(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("No call events found in trace.")

    dispatch_by_index: list[str] = []
    for m in matches:
        bare = m.group("func").rsplit(".", 1)[1]
        if bare != "write_into":
            continue
        line = int(m.group("lineno"))
        if line not in WRITE_INTO_DEF_LINE_TO_CLASS:
            raise ValueError(f"Unexpected write_into def-line: {line}")
        dispatch_by_index.append(WRITE_INTO_DEF_LINE_TO_CLASS[line])

    if not dispatch_by_index:
        raise ValueError("No write_into call events found.")

    return {
        "write_into_dispatch_per_block_index": dispatch_by_index,
        "block_count": len(dispatch_by_index),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/webvtt_block_write_into_dispatch/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/webvtt_block_write_into_dispatch/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_dispatch(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/webvtt_block_write_into_dispatch_test.py`, class "
            "`TestWebvttBlockWriteIntoDispatchQA`, method "
            "`test_webvtt_block_write_into_dispatch_case`. "
            "The test calls `list(yt_dlp.webvtt.parse_fragment(WEBVTT_BYTES))` once on the "
            "exact `WEBVTT_INPUT` literal at the top of the test file (a single Magic "
            "header with X-TIMESTAMP-MAP, then a cue body, then a `NOTE` block, then "
            "another cue body), collects the yielded `blocks` into a list, then iterates "
            "`for block in blocks: block.write_into(out)` writing to a `StringIO`. "
            "yt-dlp's `webvtt.py` defines THREE `write_into` methods: "
            "`Block.write_into` at line 134 (`stream.write(self.raw)`), "
            "`Magic.write_into` at line 221 (the elaborate header serializer), and "
            "`CueBlock.write_into` at line 311 (the cue serializer). "
            "Other classes -- `HeaderBlock`, `StyleBlock`, `RegionBlock`, `CommentBlock` -- "
            "do NOT define their own `write_into`; calling `.write_into(...)` on an "
            "instance of those classes follows MRO up to the nearest ancestor that does. "
            "For each call site `block.write_into(out)` inside the test's for-loop "
            "(one per block in `blocks` in encounter order, beginning at index 0), report "
            "which CONCRETE CLASS's `write_into` body actually executed -- i.e. the class "
            "where the runtime-dispatched method was DEFINED, NOT the runtime type of the "
            "block instance. Important: a `CommentBlock` instance dispatches to "
            "`Block.write_into` (the inherited base), not to `CommentBlock.write_into`, "
            "because `CommentBlock` does not override the method. "
            "Return a JSON object with two keys: "
            "`write_into_dispatch_per_block_index` -- a list of the bare class names "
            "(`\"Block\"`, `\"Magic\"`, or `\"CueBlock\"`) in for-loop iteration order, "
            "one entry per block iterated -- and `block_count` (int, the length of that "
            "list)."
        ),
        "template_answer": {
            "write_into_dispatch_per_block_index": ["str"],
            "block_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
