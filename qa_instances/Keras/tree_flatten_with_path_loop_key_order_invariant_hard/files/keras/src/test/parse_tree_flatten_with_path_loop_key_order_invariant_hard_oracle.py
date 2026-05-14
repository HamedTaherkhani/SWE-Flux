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


def parse_literal_or_raw(raw: str):
    try:
        return ast.literal_eval(raw)
    except Exception:
        return raw


def is_non_decreasing(seq: list) -> tuple[bool, int | None]:
    for i in range(1, len(seq)):
        prev = seq[i - 1]
        curr = seq[i]
        try:
            if curr < prev:
                return False, i
        except TypeError:
            if repr(curr) < repr(prev):
                return False, i
    return True, None


def evaluate_segment(segment_text: str):
    stack = []
    observations = 0
    loop_frames_checked = 0
    counterexample = None

    for line in segment_text.splitlines():
        m = TRACE_LINE_RE.match(line)
        if not m:
            continue

        line_no = int(m.group(1))
        event = m.group(2)
        locals_dict = parse_locals_dict(m.group(3))

        if event == "call":
            path = parse_literal_or_raw(locals_dict.get("path", ""))
            stack.append(
                {
                    "path": path,
                    "keys_line_172": [],
                    "keys_line_177": [],
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
            key = parse_literal_or_raw(locals_dict["key"])
            if line_no == 173:
                stack[-1]["keys_line_172"].append(key)
            else:
                stack[-1]["keys_line_177"].append(key)
            observations += 1
            continue

        if event == "return":
            if not stack:
                continue
            frame = stack.pop()
            for loop_line, keys in (
                (172, frame["keys_line_172"]),
                (177, frame["keys_line_177"]),
            ):
                if len(keys) < 2:
                    continue
                loop_frames_checked += 1
                ok, bad_index = is_non_decreasing(keys)
                if not ok and counterexample is None:
                    counterexample = {
                        "path": repr(frame["path"]),
                        "loop_line": loop_line,
                        "step": bad_index,
                        "prev_key": repr(keys[bad_index - 1]),
                        "curr_key": repr(keys[bad_index]),
                        "observed_keys": [repr(k) for k in keys],
                    }

    return observations, loop_frames_checked, counterexample


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/tree_flatten_with_path_loop_key_order_invariant_hard/trace.log",
    )
    p.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/tree_flatten_with_path_loop_key_order_invariant_hard/oracle.json",
    )
    args = p.parse_args()

    text = Path(args.trace_log).read_text(encoding="utf-8")
    segments = [s for s in text.split("[TRACE][START]") if s.strip()]

    total_observations = 0
    total_loop_frames_checked = 0
    holds = True
    cex = None

    for seg_idx, segment_text in enumerate(segments):
        observations, loop_frames_checked, seg_cex = evaluate_segment(
            segment_text
        )
        total_observations += observations
        total_loop_frames_checked += loop_frames_checked
        if seg_cex is not None and cex is None:
            holds = False
            cex = {"segment": seg_idx, **seg_cex}

    qa = {
        "question_kind": "M7_Invariants",
        "question": (
            "Use `keras/src/test/tree/tree_flatten_with_path_loop_key_order_invariant_hard_test.py`, "
            "class `TreeFlattenWithPathLoopKeyOrderInvariantHardQATest`, and all 12 test methods. "
            "These tests call `keras.src.tree.dmtree_impl.flatten_with_path(...)` on diverse nested "
            "structures with mixtures of `dict`, `list`/`tuple`, and `collections.OrderedDict`. "
            "In `keras/src/tree/dmtree_impl.py`, function `_recursive_flatten_with_path`, consider the "
            "child-iteration loops at lines 172 (`for key, value in zip(paths, flat)`) and 177 "
            "(`for key in sorted(structure)`). Is this loop invariant always true across the full trace: "
            "within each individual function call frame, keys observed across successive loop iterations "
            "are non-decreasing in order?"
        ),
        "oracle_answer": {
            "invariant_exists": holds
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
