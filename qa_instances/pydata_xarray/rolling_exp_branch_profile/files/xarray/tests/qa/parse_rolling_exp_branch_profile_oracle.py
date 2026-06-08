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

TARGET_CONDITIONS = [
    "n_desired < 1",
    "array.size == 0",
    "n_desired < array.size",
    "isinstance(array, Variable)",
]


def _load_condition_lines(source_text: str) -> dict[int, dict[str, object]]:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "first_n_items":
            fn = node
            break
    if fn is None:
        raise ValueError("first_n_items not found in source.")

    by_lineno: dict[int, dict[str, object]] = {}
    for idx, node in enumerate(fn.body):
        if not isinstance(node, ast.If):
            continue
        expr = ast.unparse(node.test).strip()
        if expr not in TARGET_CONDITIONS:
            continue

        true_line = node.body[0].lineno if node.body else None
        if node.orelse:
            false_line = node.orelse[0].lineno
        else:
            false_line = fn.body[idx + 1].lineno if idx + 1 < len(fn.body) else None

        by_lineno[node.lineno] = {
            "condition": expr,
            "true_line": true_line,
            "false_line": false_line,
        }

    seen = {entry["condition"] for entry in by_lineno.values()}
    missing = [expr for expr in TARGET_CONDITIONS if expr not in seen]
    if missing:
        raise ValueError(f"Could not map condition lines for: {missing}")
    return by_lineno


def extract_branch_profile(trace_text: str, source_text: str) -> dict[str, list[str]]:
    condition_by_lineno = _load_condition_lines(source_text)
    outcomes: dict[str, list[str]] = {expr: [] for expr in TARGET_CONDITIONS}

    line_events: list[int] = []
    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith(".first_n_items"):
            continue
        line_events.append(int(m.group("lineno")))

    for i in range(len(line_events) - 1):
        lineno = line_events[i]
        next_line = line_events[i + 1]
        entry = condition_by_lineno.get(lineno)
        if entry is None:
            continue

        condition = str(entry["condition"])
        true_line = entry["true_line"]
        false_line = entry["false_line"]

        if true_line is not None and next_line == true_line:
            label = f"{condition} == True"
        elif false_line is not None and next_line == false_line:
            label = f"{condition} == False"
        else:
            continue

        if label not in outcomes[condition]:
            outcomes[condition].append(label)

    compact = {
        "executed_branches": [
            {"condition": expr, "outcomes": vals}
            for expr, vals in outcomes.items()
            if vals
        ]
    }
    if not compact["executed_branches"]:
        raise ValueError("No target condition outcomes were captured from trace.")
    return compact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/rolling_exp_branch_profile/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/rolling_exp.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/rolling_exp_branch_profile/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_branch_profile(trace_text, source_text)

    qa = {
        "question_kind": "S1_IntraProceduralCFG",
        "question": (
            "Use `xarray/tests/qa/rolling_exp_branch_profile_test.py`, class "
            "`TestRollingExpBranchProfileHardQA`, method "
            "`test_rolling_exp_branch_profile_case`. "
            "During this full test execution, focus on `xarray/core/formatting.py::first_n_items`. "
            "For each conditional predicate in that function (`n_desired < 1`, `array.size == 0`, "
            "`n_desired < array.size`, `isinstance(array, Variable)`), which branch outcomes were "
            "executed at least once (True branch and/or False branch)? "
            "Return the executed outcomes per predicate."
        ),
        "template_answer": {
            "executed_branches": [
                {
                    "condition": "str",
                    "outcomes": ["str"],
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
