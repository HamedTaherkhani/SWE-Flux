#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/(?:figure|_tight_layout)\.py):(?P<lineno>\d+) "
    r"(?P<func>matplotlib\.(?:figure\.Figure\.get_tightbbox|_tight_layout\..*)) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/_tight_layout\.py):(?P<lineno>\d+) "
    r"(?P<func>matplotlib\._tight_layout\.get_tight_layout_figure) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _to_jsonable(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, 10)
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return str(value)


def parse_bbox_repr(bbox_str: str) -> dict:
    try:
        match = re.search(r'Bbox\(.*?\[\[([0-9.\-e]+),\s*([0-9.\-e]+)\],\s*\[([0-9.\-e]+),\s*([0-9.\-e]+)\]\]', bbox_str)
        if match:
            x0, y0, x1, y1 = match.groups()
            return {
                "x0": round(float(x0), 8),
                "y0": round(float(y0), 8),
                "x1": round(float(x1), 8),
                "y1": round(float(y1), 8)
            }
    except:
        pass
    return {"repr": str(bbox_str)[:200]}


def extract_output(trace_text: str) -> dict:
    return_matches = list(RETURN_RE.finditer(trace_text))
    line_matches = list(LINE_RE.finditer(trace_text))
    
    result = {
        "get_tightbbox_call_count": 0,
        "tight_layout_traced": False,
        "first_bbox": None,
        "constraint_variables_found": []
    }
    
    for match in return_matches:
        func_name = match.group("func")
        if "get_tightbbox" in func_name:
            result["get_tightbbox_call_count"] += 1
            retval_str = match.group("retval")
            
            if result["first_bbox"] is None:
                result["first_bbox"] = parse_bbox_repr(retval_str)
    
    for match in line_matches:
        result["tight_layout_traced"] = True
        locals_str = match.group("locals")
        lineno = int(match.group("lineno"))
        
        try:
            parsed_locals = ast.literal_eval(locals_str)
            
            if lineno in range(180, 220):
                for var_name in ["pos", "tight_bbox", "h_pad", "w_pad"]:
                    if var_name in parsed_locals:
                        result["constraint_variables_found"].append({
                            "line": lineno,
                            "var": var_name,
                            "repr": str(parsed_locals[var_name])[:150]
                        })
        except:
            pass
    
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/layout_tight_constrained_geometry_state_extreme/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/layout_tight_constrained_geometry_state_extreme/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/layout_tight_constrained_geometry_state_extreme_test.py`, class "
            "`TestLayoutTightConstrainedGeometryStateExtremeQA`, method "
            "`test_layout_tight_constrained_geometry_state_extreme_case`. "
            "In that test, lines 12-18 create a Figure with a 3x3 GridSpec with custom spacing parameters "
            "(hspace=0.3, wspace=0.4, left=0.1, right=0.95, top=0.92, bottom=0.08). Lines 20-36 populate "
            "all 9 subplots with complex plot elements including data lines, labels, titles, legends, and grids. "
            "Line 38-39 add a figure suptitle. Line 41 gets the renderer via `fig.canvas.get_renderer()`. "
            "Line 43 calls `tight_bbox_raw = fig.get_tightbbox(renderer)` which internally invokes matplotlib's "
            "geometry calculation system to compute the minimum bounding box containing all artists. "
            "Line 45 calls `fig.tight_layout(rect=[0, 0.03, 1, 0.95])` which triggers the constraint-based layout "
            "engine, involving `_tight_layout.get_tight_layout_figure()` that iteratively solves for optimal "
            "subplot positions. Line 47 calls `tight_bbox_after = fig.get_tightbbox(renderer)` again after layout. "
            "During this execution, multiple calls to geometry calculation methods occur with complex state tracking. "
            "What are: (1) the total number of times `get_tightbbox` is called and returns, (2) whether the "
            "`_tight_layout.get_tight_layout_figure` function is traced during execution, (3) the bounding box "
            "coordinates (x0, y0, x1, y1) returned by the FIRST call to `get_tightbbox`, and (4) a list of "
            "constraint-related variables (pos, tight_bbox, h_pad, w_pad) encountered between lines 180-220 of "
            "_tight_layout.py during the layout solve?"
        ),
        "template_answer": {
            "get_tightbbox_call_count": "int",
            "tight_layout_traced": "bool",
            "first_bbox": {
                "x0": "float",
                "y0": "float",
                "x1": "float",
                "y1": "float"
            },
            "constraint_variables_found": [
                {
                    "line": "int",
                    "var": "str",
                    "repr": "str"
                }
            ]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
