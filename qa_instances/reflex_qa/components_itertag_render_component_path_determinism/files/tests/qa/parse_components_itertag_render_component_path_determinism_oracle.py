#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TARGET_PATH = "/testbed/reflex/components/tags/iter_tag.py"
TARGET_FUNC = "reflex.components.tags.iter_tag.IterTag.render_component"
INSTANCE_ID = "components_itertag_render_component_path_determinism"

START_RE = re.compile(r"\[TRACE\]\[START\]")
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/reflex/components/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
)


def extract_sequences(trace_text: str) -> list[list[int]]:
    sequences: list[list[int]] = []
    current: list[int] = []
    started = False

    for raw_line in trace_text.splitlines():
        if START_RE.search(raw_line):
            if started:
                sequences.append(current)
                current = []
            else:
                started = True
            continue
        if not started:
            continue

        match = LINE_RE.match(raw_line)
        if not match:
            continue
        if match.group("path") != TARGET_PATH:
            continue
        if match.group("func") != TARGET_FUNC:
            continue
        if match.group("event") != "line":
            continue
        current.append(int(match.group("lineno")))

    if started:
        sequences.append(current)
    return sequences


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log")
    parser.add_argument("--out", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json")
    args = parser.parse_args()

    sequences = extract_sequences(Path(args.trace_log).read_text(encoding="utf-8"))
    invariant_exists = (
        len(sequences) == 10
        and all(sequence for sequence in sequences)
        and all(sequence == sequences[0] for sequence in sequences[1:])
    )

    qa = {
        "question_kind": "C1_IntraProceduralCFG",
        "question": (
            "Execute test `tests/qa/components_itertag_render_component_path_determinism_test.py::"
            "TestComponentsItertagRenderComponentPathDeterminismQA::"
            "test_components_itertag_render_component_path_determinism_case` exactly 10 "
            "independent times with identical inputs. In each execution, focus on "
            "`reflex/components/tags/iter_tag.py`, function "
            "`reflex.components.tags.iter_tag.IterTag.render_component`. Count only line "
            "events whose traced function name is exactly this target function. Do repeated "
            "runs follow the exact same sequence of executed line numbers inside the target "
            "function, including repeated line numbers from multiple foreach renderings? "
            "Return JSON with exactly one key: `{\"invariant_exists\": <bool>}`."
        ),
        "template_answer": {"invariant_exists": "bool"},
        "oracle_answer": {"invariant_exists": invariant_exists},
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
