#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SELF_RE = re.compile(r"<yt_dlp\\.dispatching\\.(?P<cls>\\w+) object at 0x[0-9a-fA-F]+>")


def _find_callsite_lineno(source_text: str) -> int:
    needle = "out = handler.process(ctx)"
    for i, line in enumerate(source_text.splitlines(), start=1):
        if needle in line:
            return i
    raise ValueError("Could not locate handler.process callsite in source.")


def extract_answer(trace_text: str) -> dict[str, object]:
    for line in trace_text.splitlines():
        norm = line.replace("\\", "/")
        if "yt_dlp/dispatching.py" not in norm:
            continue
        if "yt_dlp.dispatching.process event=call" not in norm:
            continue
        m = SELF_RE.search(norm)
        if m:
            return {"concrete_process_class": m.group("cls")}
    raise ValueError("Did not observe any process() call in yt_dlp/dispatching.py trace.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/dispatch_process_dynamic_target/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/dispatch_process_dynamic_target/oracle.json",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/dispatching.py",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source).read_text(encoding="utf-8")
    lineno = _find_callsite_lineno(source_text)
    answer = extract_answer(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/dispatch_process_dynamic_target_test.py`, class "
            "`TestDispatchProcessDynamicTargetQA`, method "
            "`test_dispatch_process_dynamic_target_case`. In `yt_dlp/dispatching.py`, "
            f"at line {lineno}, the code calls `handler.process(ctx)` (exactly: `out = handler.process(ctx)`). "
            "Which concrete class's `process` method implementation is actually executed at runtime? "
            "Return the class name as `concrete_process_class` (read it from the `self` value on the "
            "trace line for that `process` call)."
        ),
        "template_answer": {"concrete_process_class": "str"},
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

