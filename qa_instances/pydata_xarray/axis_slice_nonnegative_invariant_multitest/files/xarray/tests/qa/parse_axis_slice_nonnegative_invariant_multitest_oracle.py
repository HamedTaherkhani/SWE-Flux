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


def _locate_lines(source_text: str) -> dict[str, dict[str, int]]:
    tree = ast.parse(source_text)
    out: dict[str, dict[str, int]] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {"trapz", "cumulative_trapezoid"}:
            start = node.body[0].lineno
            target = None
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    if any(isinstance(t, ast.Name) and t.id == "x_sl1" for t in child.targets):
                        target = child.lineno
                        break
            if target is None:
                raise ValueError(f"Could not find x_sl1 assignment in {node.name}.")
            out[node.name] = {"start": start, "target": target}
    if set(out) != {"trapz", "cumulative_trapezoid"}:
        raise ValueError("Missing trapz/cumulative_trapezoid line mapping.")
    return out


def extract_invariant(trace_text: str, source_text: str) -> dict[str, object]:
    lines = _locate_lines(source_text)
    current_axis: dict[str, int | None] = {"trapz": None, "cumulative_trapezoid": None}
    observed_axis: list[int] = []

    for m in LINE_RE.finditer(trace_text):
        func_full = m.group("func")
        if func_full.endswith(".trapz"):
            fn = "trapz"
        elif func_full.endswith(".cumulative_trapezoid"):
            fn = "cumulative_trapezoid"
        else:
            continue

        lineno = int(m.group("lineno"))
        locals_map = ast.literal_eval(m.group("locals"))

        if lineno == lines[fn]["start"]:
            current_axis[fn] = None

        if "axis" in locals_map:
            try:
                current_axis[fn] = int(ast.literal_eval(locals_map["axis"]))
            except Exception:
                pass

        if lineno == lines[fn]["target"] and current_axis[fn] is not None:
            observed_axis.append(current_axis[fn])  # value used at slice-construction point

    if not observed_axis:
        raise ValueError("No axis observations captured at target points.")

    is_invariant = all(v >= 0 for v in observed_axis)
    return {
        "is_invariant": is_invariant,
        "observed_axis_values": sorted(set(observed_axis)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/axis_slice_nonnegative_invariant_multitest/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/duck_array_ops.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/axis_slice_nonnegative_invariant_multitest/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_invariant(trace_text, source_text)

    qa = {
        "question_kind": "M7_Invariants",
        "question": (
            "Use `xarray/tests/qa/axis_slice_nonnegative_invariant_multitest_test.py`, class "
            "`TestAxisSliceNonnegativeInvariantMultitestHardQA`, and execute the full suite in that file "
            "(both test methods). During this suite, inspect `xarray/core/duck_array_ops.py` functions "
            "`trapz` and `cumulative_trapezoid`. At the line where `x_sl1` is assigned in each function, "
            "is the property `axis >= 0` an invariant across all executions? Return whether it is invariant "
            "and the unique observed axis values at those points."
        ),
        "template_answer": {
            "is_invariant": "bool",
            "observed_axis_values": ["int"],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
