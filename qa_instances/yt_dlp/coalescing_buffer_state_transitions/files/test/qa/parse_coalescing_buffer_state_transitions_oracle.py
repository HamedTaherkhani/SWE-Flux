#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

TRACE_SUFFIX = "yt_dlp/coalescing_buffer.py"
FUNC_SUFFIX = ".schedule_window_merge"
TARGET_VAR = "status"


def _parse_locals_blob(blob: str) -> dict[str, str]:
    blob = blob.strip()
    if not blob.startswith("{") or not blob.endswith("}"):
        return {}
    try:
        raw = ast.literal_eval(blob)
    except (ValueError, SyntaxError):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        out[str(k)] = str(v)
    return out


def extract_status_values(trace_text: str) -> dict[str, object]:
    """Ordered values assigned to `status` in schedule_window_merge (from changed locals)."""
    marker = " event=line locals="
    values: list[str] = []

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
        if not func.endswith(FUNC_SUFFIX):
            continue
        try:
            path_part, _lineno = rest.rsplit(":", 1)
        except ValueError:
            continue
        if not path_part.replace("\\", "/").endswith(TRACE_SUFFIX):
            continue

        loc = _parse_locals_blob(loc_blob)
        if TARGET_VAR not in loc:
            continue
        raw_v = loc[TARGET_VAR]
        try:
            values.append(ast.literal_eval(raw_v))
        except (ValueError, SyntaxError):
            values.append(raw_v)

    if not values:
        raise ValueError(
            f"No trace events recorded assignments to {TARGET_VAR!r} in {TRACE_SUFFIX}."
        )
    return {"status_values": values}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/coalescing_buffer_state_transitions/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/coalescing_buffer_state_transitions/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    oracle_answer = extract_status_values(trace_text)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `test/qa/coalescing_buffer_state_transitions_test.py`, class "
            "`TestCoalescingBufferStateTransitionsQA`, method "
            "`test_coalescing_buffer_state_transitions_case`. Consider execution of "
            "`schedule_window_merge` in `yt_dlp/coalescing_buffer.py` triggered by that test "
            "(same arguments as the call inside the test). The local name `status` is assigned "
            "repeatedly along the real path taken. Return `status_values` as the ordered list "
            "of every string value that is assigned to `status` during that single call, "
            "from first assignment to last (include duplicates if the same literal is assigned "
            "more than once on the executed path). Do not include values that are only read or "
            "compared; only right-hand assignments to `status`."
        ),
        "template_answer": {"status_values": ["str"]},
        "oracle_answer": oracle_answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
