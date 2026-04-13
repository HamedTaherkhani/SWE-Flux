#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

TRACE_SUFFIX = "yt_dlp/radix_codec.py"
FUNC_SUFFIX = ".merge_stride_totals"


def _loop_body_entry_lineno(source_text: str) -> int:
    tree = ast.parse(source_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "merge_stride_totals":
            for stmt in node.body:
                if isinstance(stmt, ast.While) and stmt.body:
                    return stmt.body[0].lineno
    raise ValueError("Could not find while-loop body entry line in merge_stride_totals.")


def extract_loop_iterations(trace_text: str, *, source_text: str) -> dict[str, object]:
    target_line = _loop_body_entry_lineno(source_text)
    marker = " event=line locals="
    count = 0

    for raw_line in trace_text.splitlines():
        line = raw_line.strip()
        if marker not in line:
            continue
        pre, _loc = line.split(marker, 1)
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
            _path_part, lineno_str = rest.rsplit(":", 1)
        except ValueError:
            continue
        if not lineno_str.isdigit():
            continue
        if int(lineno_str) != target_line:
            continue
        count += 1

    if count == 0:
        raise ValueError(
            "No line events matched the loop body entry line for merge_stride_totals "
            f"(expected lineno {target_line} in {TRACE_SUFFIX})."
        )
    return {"loop_body_iterations": count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/radix_slot_walk_probe/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/radix_slot_walk_probe/oracle.json",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/radix_codec.py",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source).read_text(encoding="utf-8")
    oracle_answer = extract_loop_iterations(trace_text, source_text=source_text)

    qa = {
        "question_kind": "iterations",
        "question": (
            "Use `test/qa/radix_slot_walk_probe_test.py`, class `TestRadixSlotWalkProbeQA`, method "
            "`test_radix_slot_walk_probe_case`. Inside `yt_dlp/radix_codec.py`, function "
            "`merge_stride_totals`, focus on the single `while` loop whose header is `while i < limit:`. "
            "Count how many times the loop body runs for the arguments passed in this test "
            "(each time the condition is true and control enters the body counts as one). "
            "Do not count the final failed condition check after the last body execution. Return "
            "the count as the integer `loop_body_iterations`."
        ),
        "template_answer": {"loop_body_iterations": "int"},
        "oracle_answer": oracle_answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
