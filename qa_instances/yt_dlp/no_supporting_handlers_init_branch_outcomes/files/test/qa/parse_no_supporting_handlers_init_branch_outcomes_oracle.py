#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

TARGET_PATH = Path("/testbed/yt_dlp/networking/exceptions.py")
TARGET_CLASS = "NoSupportingHandlers"
TARGET_FUNC_NAME = "__init__"


# Trace plugin records every `event=line` for `__init__` whose source file is
# /testbed/yt_dlp/networking/exceptions.py. Walk events in order; for each
# `if`/`elif` predicate line in the target body, classify the next line event
# (within the same call) as `true` (entered the body) or `false` (skipped past
# the body to the next sibling statement).
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/networking/exceptions\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.networking\.exceptions\.__init__) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)


def find_target_function(module: ast.Module) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == TARGET_CLASS:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == TARGET_FUNC_NAME:
                    return child
    raise ValueError(f"Could not find {TARGET_CLASS}.{TARGET_FUNC_NAME} in target file.")


def collect_conditionals(func_node: ast.FunctionDef):
    """For each `if/elif` predicate, return:
        (condition_line, condition_text, body_lines_set, after_body_line)
    where `body_lines_set` is the set of source lines in the immediate `if`
    body (NOT recursing into nested ifs' bodies for THIS conditional's record),
    and `after_body_line` is the first source line that executes when the
    predicate is false (i.e. the `else`/`elif` body's first line, or the next
    statement after the whole if/elif chain). We use these to classify
    branches as `true` (next event in body lines) or `false` (next event at or
    past after_body_line)."""
    func_src_lines = set(range(func_node.lineno, func_node.end_lineno + 1))
    conditionals = []

    for parent in ast.walk(func_node):
        if isinstance(parent, ast.If):
            cond_line = parent.lineno
            body_lines: set[int] = set()
            for stmt in parent.body:
                body_lines.update(range(stmt.lineno, stmt.end_lineno + 1))
            cond_text = ast.unparse(parent.test) if hasattr(ast, "unparse") else "<ast.unparse unavailable>"
            conditionals.append({
                "line": cond_line,
                "condition": cond_text,
                "body_lines": body_lines,
            })

    conditionals.sort(key=lambda c: c["line"])
    return conditionals


def extract_branch_outcomes(trace_text: str, conditionals) -> list[dict]:
    # Group line events into per-call sequences so we don't accidentally pair
    # a condition fire from one call with a body line from another.
    calls: list[list[int]] = []
    current: list[int] | None = None
    for m in LINE_RE.finditer(trace_text):
        ev = m.group("event")
        ln = int(m.group("lineno"))
        if ev == "call":
            current = []
            calls.append(current)
            continue
        if ev in {"return", "exception"}:
            current = None
            continue
        if ev == "line" and current is not None:
            current.append(ln)

    cond_lines = [c["line"] for c in conditionals]
    body_lines = {c["line"]: c["body_lines"] for c in conditionals}

    branches_per_cond: dict[int, set[str]] = defaultdict(set)

    for sequence in calls:
        for i, ln in enumerate(sequence):
            if ln not in cond_lines:
                continue
            # find next line event in this same call
            next_ln = None
            for j in range(i + 1, len(sequence)):
                next_ln = sequence[j]
                break
            if next_ln is None:
                continue
            if next_ln in body_lines[ln]:
                branches_per_cond[ln].add("true")
            else:
                branches_per_cond[ln].add("false")

    out = []
    for c in conditionals:
        observed = sorted(branches_per_cond.get(c["line"], set()))
        if not observed:
            continue
        out.append({
            "line": c["line"],
            "condition": c["condition"],
            "branches_executed": observed,
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/no_supporting_handlers_init_branch_outcomes/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/no_supporting_handlers_init_branch_outcomes/oracle.json",
    )
    args = parser.parse_args()

    src_text = TARGET_PATH.read_text(encoding="utf-8")
    func_node = find_target_function(ast.parse(src_text))
    conditionals = collect_conditionals(func_node)

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    condition_branches = extract_branch_outcomes(trace_text, conditionals)

    qa = {
        "question_kind": "conditional_statements",
        "question": (
            "Run the FULL test suite in "
            "`test/qa/no_supporting_handlers_init_branch_outcomes_test.py` (all test "
            "methods in class `TestNoSupportingHandlersInitBranchOutcomesQA`, three tests "
            "total). Each test constructs a "
            "`yt_dlp.networking.exceptions.NoSupportingHandlers` -- whose `__init__` is "
            "defined at line 33 in `yt_dlp/networking/exceptions.py` -- with different "
            "combinations of `unsupported_errors` and `unexpected_errors`. "
            "`__init__` contains exactly two `if` predicates: "
            "(1) line 43 `if unexpected_errors:` (body line 44 reassigns `reason_str` to "
            "include the unexpected-errors count), and "
            "(2) line 47 `if reason_str:` (body line 48 appends `: {reason_str}` to "
            "`err_str`). "
            "For each evaluated condition line in this function, report which BRANCH "
            "OUTCOMES were executed across the entire test suite. In `branches_executed`, "
            "use `\"true\"` if that condition evaluated to true at least once (so "
            "execution entered the `if` block body for that line), and `\"false\"` if it "
            "evaluated to false at least once (so execution skipped the body and "
            "continued past the `if` block). If both happened across different evaluations "
            "of the same line, include both values. "
            "Return a JSON object with key `condition_branches` whose value is an array of "
            "objects in ascending line-number order, each shaped exactly as "
            "`{\"line\": <int>, \"condition\": <exact condition source text>, "
            "\"branches_executed\": [<\"false\" and/or \"true\">]}`. Include only "
            "condition lines that were evaluated at least once."
        ),
        "template_answer": {
            "condition_branches": [],
        },
        "oracle_answer": {
            "condition_branches": condition_branches,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
