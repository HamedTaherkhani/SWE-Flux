#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _locate_lines(source_text: str) -> tuple[int, int]:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "remove_incompatible_items":
            fn = node
            break
    if fn is None:
        raise ValueError("remove_incompatible_items not found.")

    start_line = fn.body[0].lineno
    loop_line = None
    for node in fn.body:
        if isinstance(node, ast.For):
            loop_line = node.lineno
            break
    if loop_line is None:
        raise ValueError("Target loop not found in remove_incompatible_items.")
    return start_line, loop_line


def _dict_len(value_repr: str) -> int:
    value = ast.literal_eval(value_repr)
    if not isinstance(value, dict):
        raise ValueError("first_dict repr is not a dict.")
    return len(value)


def _classify_relation(sequences: list[list[int]]) -> str:
    deltas: list[int] = []
    for seq in sequences:
        for i in range(len(seq) - 1):
            deltas.append(seq[i + 1] - seq[i])
    if not deltas:
        return "neither"
    if all(d < 0 for d in deltas):
        return "decreases"
    if all(d > 0 for d in deltas):
        return "increases"
    return "neither"


def extract_relation(trace_text: str, source_text: str) -> dict[str, object]:
    start_line, loop_line = _locate_lines(source_text)
    current_first_len: int | None = None
    current_seq: list[int] = []
    sequences: list[list[int]] = []

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith(".remove_incompatible_items"):
            continue

        lineno = int(m.group("lineno"))
        locals_map = ast.literal_eval(m.group("locals"))

        if lineno == start_line:
            if current_seq:
                sequences.append(current_seq)
            current_seq = []
            current_first_len = None

        if "first_dict" in locals_map:
            current_first_len = _dict_len(locals_map["first_dict"])

        if lineno == loop_line and current_first_len is not None:
            current_seq.append(current_first_len)

    if current_seq:
        sequences.append(current_seq)

    sequences = [s for s in sequences if len(s) >= 2]
    if not sequences:
        raise ValueError("No loop-length sequences captured for monotonic analysis.")

    relation = _classify_relation(sequences)
    return {
        "variable_x": "loop_iteration_index",
        "variable_y": "len(first_dict)",
        "relationship": relation,
        "observed_len_sequences": sequences,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/dict_loop_relation_profile/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/utils.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/dict_loop_relation_profile/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_relation(trace_text, source_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use `xarray/tests/qa/dict_loop_relation_profile_test.py`, class "
            "`TestDictLoopRelationProfileHardQA`, and execute the full suite in that file "
            "(both test methods). During this suite, inspect `xarray/core/utils.py::"
            "remove_incompatible_items`, focusing on the loop `for k in list(first_dict):`. "
            "Let variable X be the loop iteration index (in increasing order) and variable Y be "
            "`len(first_dict)` measured at the start of each loop iteration. "
            "As X increases, does Y increase, decrease, or neither?"
        ),
        "template_answer": {
            "variable_x": "str",
            "variable_y": "str",
            "relationship": "str",
            "observed_len_sequences": [["int"]],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
