#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/layout/ratiotile\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.layout\.ratiotile\.(?:GridInfo\.)?get_sizes) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find GridInfo.get_sizes return events in trace log.")

    # Single call in this test; use the last match for safety.
    target = matches[-1]
    locals_dict = ast.literal_eval(target.group("locals"))

    def to_int(name: str) -> int:
        if name not in locals_dict:
            raise ValueError(f"Missing expected local variable: {name}")
        return int(str(locals_dict[name]))

    output = {
        "loop_variable_state": {
            "orientation": to_int("orientation"),
            "i": to_int("i"),
            "j": to_int("j"),
            "x": to_int("x"),
            "y": to_int("y"),
            "width": to_int("width"),
            "height": to_int("height"),
        }
    }
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/ratiotile_indirect_get_sizes_loop_var_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/ratiotile_indirect_get_sizes_loop_var_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/ratiotile_indirect_get_sizes_loop_var_state_test.py`, class "
            "`TestRatioTileIndirectGetSizesLoopVarStateQA`, method "
            "`test_ratiotile_indirect_get_sizes_loop_var_state_case`. "
            "This test calls `layout.configure(windows[3], DummyRect(17, 29, 997, 743))` on "
            "`RatioTile(ratio=0.63, fancy=False)` with 11 windows. "
            "In `libqtile/layout/ratiotile.py`, `RatioTile.configure` indirectly calls "
            "`GridInfo.get_sizes(...)` (method starting at line 152), which uses nested loops and "
            "conditional return when `len(results) == self.num_windows`. "
            "At that return point (after loop/conditional execution), what are the exact values of "
            "`orientation`, `i`, `j`, `x`, `y`, `width`, and `height`?"
        ),
        "template_answer": {
            "loop_variable_state": {
                "orientation": "int",
                "i": "int",
                "j": "int",
                "x": "int",
                "y": "int",
                "width": "int",
                "height": "int",
            }
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
