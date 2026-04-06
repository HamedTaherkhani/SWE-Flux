#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


TRACE_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"/testbed/keras/src/tree/dmtree_impl.py:(\d+) "
    r"keras\.src\.tree\.dmtree_impl\._recursive_flatten_with_path "
    r"event=(call|line|return) locals=(\{.*\})$"
)


def parse_locals_dict(raw: str) -> dict:
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


def parse_key(raw: str) -> str:
    try:
        parsed = ast.literal_eval(raw)
        return str(parsed)
    except Exception:
        return raw


def evaluate_segment(segment_text: str):
    stack = []
    num_obs = 0
    up_witness = None
    down_witness = None

    for line in segment_text.splitlines():
        m = TRACE_LINE_RE.match(line)
        if not m:
            continue

        line_no = int(m.group(1))
        event = m.group(2)
        locals_dict = parse_locals_dict(m.group(3))

        if event == "call":
            path_raw = locals_dict.get("path", "")
            stack.append(
                {
                    "path": path_raw,
                    "line_172_keys": [],
                    "line_177_keys": [],
                }
            )
            continue

        if event == "line":
            if not stack:
                continue
            if line_no not in (173, 178):
                continue
            if "key" not in locals_dict:
                continue
            key = parse_key(locals_dict["key"])
            if line_no == 173:
                stack[-1]["line_172_keys"].append(key)
            else:
                stack[-1]["line_177_keys"].append(key)
            continue

        if event == "return":
            if not stack:
                continue
            frame = stack.pop()
            for loop_line, keys in (
                (172, frame["line_172_keys"]),
                (177, frame["line_177_keys"]),
            ):
                if len(keys) < 2:
                    continue
                for i in range(1, len(keys)):
                    num_obs += 1
                    prev_key = keys[i - 1]
                    curr_key = keys[i]
                    if curr_key > prev_key and up_witness is None:
                        up_witness = {
                            "path": frame["path"],
                            "loop_line": loop_line,
                            "step": i,
                            "prev_key": prev_key,
                            "curr_key": curr_key,
                        }
                    if curr_key < prev_key and down_witness is None:
                        down_witness = {
                            "path": frame["path"],
                            "loop_line": loop_line,
                            "step": i,
                            "prev_key": prev_key,
                            "curr_key": curr_key,
                        }

    return num_obs, up_witness, down_witness


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/tree_key_iteration_trend_profile/trace.log",
    )
    p.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/tree_key_iteration_trend_profile/oracle.json",
    )
    args = p.parse_args()

    text = Path(args.trace_log).read_text(encoding="utf-8")
    segments = [s for s in text.split("[TRACE][START]") if s.strip()]

    total_obs = 0
    first_up = None
    first_down = None

    for seg_idx, segment in enumerate(segments):
        num_obs, up_witness, down_witness = evaluate_segment(segment)
        total_obs += num_obs
        if up_witness is not None and first_up is None:
            first_up = {"segment": seg_idx, **up_witness}
        if down_witness is not None and first_down is None:
            first_down = {"segment": seg_idx, **down_witness}

    holds = first_up is not None and first_down is not None
    counterexample = None
    if not holds:
        counterexample = {
            "missing_direction": "increase" if first_up is None else "decrease",
            "increase_witness": first_up,
            "decrease_witness": first_down,
        }

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use `keras/src/test/tree/tree_key_iteration_trend_profile_test.py`, class "
            "`TreeKeyIterationTrendProfileQATest`, and all 12 test methods. These tests call "
            "`keras.src.tree.dmtree_impl.flatten_with_path(...)` on diverse nested structures containing both "
            "`dict` and `collections.OrderedDict`. In `keras/src/tree/dmtree_impl.py`, function "
            "`_recursive_flatten_with_path`, consider loop iterations at lines 172 and 177 (observed via key "
            "updates at lines 173 and 178). If loop iteration index increases, is the key-trend relationship "
            "across the full trace best characterized as neither monotonic increasing nor monotonic "
            "decreasing?"
        ),
        "oracle_answer": {
            "invariant_exists": holds
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
