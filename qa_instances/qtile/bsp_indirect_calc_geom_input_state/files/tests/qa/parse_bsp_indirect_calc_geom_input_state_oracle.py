#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/layout/bsp\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.layout\.bsp\.(?:_BspNode\.)?calc_geom) "
    r"event=call locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find _BspNode.calc_geom call events in trace log.")

    # Trace plugin logs changed locals only for call events, so reconstruct
    # full arg state by carrying forward previously seen values.
    current = {"x": None, "y": None, "w": None, "h": None}
    states: list[dict[str, int]] = []
    for match in matches:
        locals_dict = ast.literal_eval(match.group("locals"))
        for key in ("x", "y", "w", "h"):
            if key in locals_dict:
                current[key] = int(locals_dict[key])
        if all(current[k] is not None for k in ("x", "y", "w", "h")):
            states.append(
                {
                    "x": int(current["x"]),
                    "y": int(current["y"]),
                    "w": int(current["w"]),
                    "h": int(current["h"]),
                }
            )

    if not states:
        raise ValueError("Could not reconstruct full calc_geom input states.")

    # In this test's recursive geometry walk, the last full state corresponds
    # to the deepest right-most leaf after all pre-configure mutations.
    last = states[-1]
    x = last["x"]
    y = last["y"]
    w = last["w"]
    h = last["h"]

    return {"input_state": {"x": x, "y": y, "w": w, "h": h}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/bsp_indirect_calc_geom_input_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/bsp_indirect_calc_geom_input_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/bsp_indirect_calc_geom_input_state_test.py`, class "
            "`TestBspIndirectCalcGeomInputStateQA`, method "
            "`test_bsp_indirect_calc_geom_input_state_case`. "
            "The test mutates a `Bsp` layout with 8 windows using focus/split/grow operations, "
            "then calls `layout.configure(windows[0], DummyRect(23, 41, 1531, 901))`. "
            "This is indirect testing: in `libqtile/layout/bsp.py`, `Bsp.configure` calls "
            "`self.root.calc_geom(...)`, which recursively invokes `_BspNode.calc_geom(x, y, w, h)`. "
            "At the final recursive `_BspNode.calc_geom` call triggered by that single "
            "`layout.configure(...)` invocation, what are the exact input values of `x`, `y`, `w`, and `h`?"
        ),
        "template_answer": {
            "input_state": {"x": "int", "y": "int", "w": "int", "h": "int"}
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
