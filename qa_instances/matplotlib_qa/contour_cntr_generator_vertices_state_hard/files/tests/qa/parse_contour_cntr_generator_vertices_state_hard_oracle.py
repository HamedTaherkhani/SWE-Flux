#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/_contour\.py):(?P<lineno>\d+) "
    r"(?P<func>matplotlib\._contour\.ContourGenerator\._c_module\._contour_generator\.create_contour) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

RETURN_RE_ALT = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/src/_contour\..*):(?P<lineno>\d+) "
    r"(?P<func>.*create_contour.*) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
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


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        matches = list(RETURN_RE_ALT.finditer(trace_text))
    
    if not matches:
        return {
            "vertices_count": "not_traced",
            "codes_count": "not_traced",
            "first_vertex_shape": "not_traced",
            "analysis": "create_contour not traced - likely C extension"
        }
    
    target = matches[-1]
    retval_str = target.group("retval")
    
    try:
        if retval_str.startswith("("):
            retval_parsed = ast.literal_eval(retval_str)
            vertices_list, codes_list = retval_parsed
            
            return {
                "vertices_count": len(vertices_list),
                "codes_count": len(codes_list),
                "first_vertex_repr": str(vertices_list[0])[:200] if vertices_list else "empty",
                "analysis": "successfully_extracted"
            }
    except:
        pass
    
    return {
        "retval_repr": str(retval_str)[:300],
        "analysis": "return_value_captured"
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/contour_cntr_generator_vertices_state_hard/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/contour_cntr_generator_vertices_state_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/contour_cntr_generator_vertices_state_hard_test.py`, class "
            "`TestContourCntrGeneratorVerticesStateHardQA`, method "
            "`test_contour_cntr_generator_vertices_state_hard_case`. "
            "In that test, lines 12-18 create a 25x20 meshgrid with variables X, Y, and Z where Z is computed using "
            "a complex expression involving `sin(X) * cos(Y) + 0.3 * sin(2*X) * cos(3*Y) + 0.1 * X**2 - 0.05 * Y**2` "
            "plus random noise (seed=42). Line 20 computes 8 contour levels spanning Z's range. "
            "Line 23 calls `ax.contour(X, Y, Z, levels=levels)` which internally creates a ContourGenerator object. "
            "Line 31 extracts `cntr_obj = contour_set._contour_generator`, line 33 selects `test_level = float(levels[4])`, "
            "and line 34 calls `vertices_list, codes_list = cntr_obj.create_contour(test_level)`. "
            "During this execution, the ContourGenerator's `create_contour` method processes the Z data using a marching "
            "squares algorithm to trace contour lines. This involves complex nested loops, edge detection, and vertex "
            "accumulation. What are the exact values for: (1) the total number of contour segments in `vertices_list`, "
            "(2) the total number of path codes in `codes_list`, and (3) the shape of the first vertex array "
            "`vertices_list[0]` if it exists?"
        ),
        "template_answer": {
            "vertices_count": "int | str",
            "codes_count": "int | str",
            "first_vertex_shape": "tuple[int, int] | str"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
