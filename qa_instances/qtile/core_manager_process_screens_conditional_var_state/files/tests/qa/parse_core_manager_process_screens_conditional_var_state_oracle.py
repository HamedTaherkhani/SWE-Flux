#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/core/manager\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.core\.manager\._process_screens) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

GROUP_NAME_RE = re.compile(r"DummyGroup\((?P<name>[^)]+)\)")


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find _process_screens return events in trace log.")

    target = matches[-1]
    locals_dict = ast.literal_eval(target.group("locals"))

    if "xywh" not in locals_dict:
        raise ValueError("Missing `xywh` in _process_screens locals.")
    if "grp" not in locals_dict:
        raise ValueError("Missing `grp` in _process_screens locals.")

    xywh_raw = ast.literal_eval(str(locals_dict["xywh"]))
    xywh_merged = []
    for (x, y), (w, h) in xywh_raw.items():
        xywh_merged.append({"pos": [int(x), int(y)], "size": [int(w), int(h)]})

    grp_repr = str(locals_dict["grp"])
    grp_match = GROUP_NAME_RE.search(grp_repr)
    grp_name = grp_match.group("name") if grp_match else grp_repr

    return {
        "variable_state": {
            "xywh_merged": xywh_merged,
            "final_grp_name": grp_name,
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_process_screens_conditional_var_state/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "core_manager_process_screens_conditional_var_state/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/core_manager_process_screens_conditional_var_state_test.py`, class "
            "`TestCoreManagerProcessScreensConditionalVarStateQA`, method "
            "`test_core_manager_process_screens_conditional_var_state_case`. "
            "In `libqtile/core/manager.py`, this test calls `_process_screens()` on a probe object. "
            "Inside `_process_screens`, there is a loop that builds `xywh` via repeated updates using "
            "`xywh[pos] = (max(width, info.width), max(height, info.height))`, and a nested conditional "
            "assignment path for `grp` (`current_groups` vs `get_available_group` vs `add_autogen_group`). "
            "At `_process_screens` return, what are the exact values of `xywh_merged` and `final_grp_name`?"
        ),
        "template_answer": {
            "variable_state": {
                "xywh_merged": [{"pos": ["int", "int"], "size": ["int", "int"]}],
                "final_grp_name": "str",
            }
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
