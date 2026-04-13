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


def _dict_len(value_repr: str) -> int:
    value = ast.literal_eval(value_repr)
    if not isinstance(value, dict):
        raise ValueError("first_dict repr is not a dict.")
    return len(value)


def _classify_relation(sequence: list[int]) -> str:
    deltas: list[int] = []
    for i in range(len(sequence) - 1):
        deltas.append(sequence[i + 1] - sequence[i])
    if not deltas:
        return "neither"
    if all(d < 0 for d in deltas):
        return "decreases"
    if all(d > 0 for d in deltas):
        return "increases"
    return "neither"


def extract_relation(trace_text: str, source_text: str) -> dict[str, object]:
    _ = source_text  # retained for CLI compatibility with existing eval.sh
    suite_sequence: list[int] = []

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith(".remove_incompatible_items"):
            continue

        locals_map = ast.literal_eval(m.group("locals"))
        if "first_dict" in locals_map:
            # Preserve the benchmark's current oracle semantics: use one flattened
            # suite-level sequence of all traced `first_dict` snapshots in execution order.
            suite_sequence.append(_dict_len(locals_map["first_dict"]))

    if len(suite_sequence) < 2:
        raise ValueError("No suite-level first_dict length sequence captured for analysis.")

    relation = _classify_relation(suite_sequence)
    return {
        "variable_x": "loop_iteration_index",
        "variable_y": "len(first_dict)",
        "relationship": relation,
        "observed_len_sequences": [suite_sequence],
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
    output = extract_relation(trace_text, "")

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use `xarray/tests/qa/dict_loop_relation_profile_test.py`, class "
            "`TestDictLoopRelationProfileHardQA`, and execute the full suite in that file "
            "(both test methods). During this suite, inspect `xarray/core/utils.py::"
            "remove_incompatible_items`, focusing on the loop `for k in list(first_dict):`. "
            "For this benchmark, `observed_len_sequences` must contain exactly one inner list: "
            "the single flattened chronological suite-level sequence obtained by concatenating all "
            "traced `len(first_dict)` values across both test methods in execution order. Let "
            "variable X be the position within that flattened suite-level sequence and variable Y "
            "be the corresponding `len(first_dict)` value. As X increases, does Y increase, "
            "decrease, or neither?"
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
