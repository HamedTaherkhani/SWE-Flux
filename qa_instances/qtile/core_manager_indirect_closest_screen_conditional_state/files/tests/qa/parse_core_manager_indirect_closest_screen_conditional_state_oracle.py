#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/core/manager\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.core\.manager\._find_closest_closest) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

SCREEN_NAME_RE = re.compile(r"DummyScreen\((?P<name>[^)]+)\)")


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find _find_closest_closest return events in trace log.")

    target = matches[-1]
    locals_dict = ast.literal_eval(target.group("locals"))

    if "candidate_screens" not in locals_dict:
        raise ValueError("Missing `candidate_screens` in traced locals.")
    if "closest_distance" not in locals_dict:
        raise ValueError("Missing `closest_distance` in traced locals.")

    candidate_repr = str(locals_dict["candidate_screens"])
    candidate_screen_names = SCREEN_NAME_RE.findall(candidate_repr)
    closest_distance = float(str(locals_dict["closest_distance"]))

    return {
        "variable_state": {
            "candidate_screen_names": candidate_screen_names,
            "closest_distance": closest_distance,
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_indirect_closest_screen_conditional_state/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_indirect_closest_screen_conditional_state/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/core_manager_indirect_closest_screen_conditional_state_test.py`, "
            "class `TestCoreManagerIndirectClosestScreenConditionalStateQA`, method "
            "`test_core_manager_indirect_closest_screen_conditional_state_case`. "
            "This test directly calls `qtile_probe.find_closest_screen(1479, 91)` with five "
            "overlapping `DummyScreen` objects. In `libqtile/core/manager.py`, this call enters "
            "`_find_closest_closest(...)` after multiple conditional branches. Inside that function, "
            "`candidate_screens` is reassigned by the complex conditional filter "
            "`[s for s in candidate_screens if x < s.x + s.width and y < s.y + s.height]`, and then "
            "the distance-minimization conditional updates `closest_distance`. "
            "At `_find_closest_closest` return, what are the exact ordered "
            "`candidate_screen_names` and the final `closest_distance`?"
        ),
        "template_answer": {
            "variable_state": {
                "candidate_screen_names": ["str"],
                "closest_distance": "float",
            }
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
